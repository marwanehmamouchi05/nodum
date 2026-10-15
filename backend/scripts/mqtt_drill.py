"""Real MQTT wire drill against a disposable loopback broker and SQLite database.

Run with optional Paho dependency and --broker-python pointing to a separate
test environment containing requirements-mqtt-broker-test.txt. No real sensors.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from scripts.drill_support import isolated_environment
from app.integrations.mqtt_sensor import ContactIngestor, ContactSubscriber, SensorBinding
from app.models.authorization import Principal
from app.services.authorization import AuthorizationService
from app.services.manager import ManagerService
from app.sqlite_repository import SQLiteRepository
from demo_product import seed_demo, PREFIX


def wait_for(predicate):
    deadline=time.monotonic()+12
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.05)
    raise RuntimeError('MQTT fixture acceptance deadline exceeded')


def run(broker_python, events=3):
    import paho.mqtt.client as mqtt
    with tempfile.TemporaryDirectory(prefix='nodum-mqtt-') as directory:
        env=isolated_environment()
        env.update(APP_ENV='development',AUTH_PUBLIC_ORIGIN='http://127.0.0.1',
                   DATABASE_URL='sqlite:///'+str(Path(directory)/'synthetic.db'))
        previous=dict(os.environ)
        os.environ.clear();os.environ.update(env)
        broker=None;subscriber=None;publisher=None
        try:
            repo=SQLiteRepository()
            repo.initialize(seed_demo=False)
            users=seed_demo(repo,datetime.now(timezone.utc))
            user=users['demo-presenter']
            def auth():return AuthorizationService(repo,Principal(user_id=user.id,person_id=user.person_id),datetime.now(timezone.utc))
            binding=SensorBinding(PREFIX+'building',PREFIX+'machine-room-sensor')
            ingest=ContactIngestor(auth,binding)
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            def start_broker():
                process=subprocess.Popen([str(broker_python),str(ROOT/'backend/scripts/mqtt_fixture_broker.py'),
                    '--port',str(port)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                def ready():
                    if process.poll() is not None:raise RuntimeError('Broker fixture exited')
                    try:
                        with socket.create_connection(('127.0.0.1',port),timeout=.2):return True
                    except OSError:return False
                try:
                    wait_for(ready)
                except BaseException:
                    process.terminate()
                    process.wait(timeout=10)
                    raise
                return process
            broker=start_broker()
            connected=threading.Event()
            publisher=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,protocol=mqtt.MQTTv311)
            publisher.on_connect=lambda client,userdata,flags,reason,properties:connected.set() if not reason.is_failure else None
            publisher.connect('127.0.0.1',port)
            publisher.loop_start()
            wait_for(connected.is_set)
            def sample(identifier):
                return json.dumps({'event_id':identifier,'observed_at':datetime.now(timezone.utc).isoformat(),'state':'open'}).encode()
            # Retained state is not evidence of a new observation on subscription.
            publisher.publish(binding.topic,sample('retained'),qos=1,retain=True).wait_for_publish(5)
            subscriber=ContactSubscriber(ingest,host='127.0.0.1',port=port,loopback_fixture=True)
            subscriber.start()
            wait_for(lambda:subscriber.status=='subscribed' and subscriber.counts['rejected']==1)
            started=time.monotonic()
            first=sample('event-0')
            for i in range(events):
                publisher.publish(binding.topic,first if i==0 else sample(f'event-{i}'),qos=1).wait_for_publish(5)
            publisher.publish(binding.topic,first,qos=1).wait_for_publish(5)
            publisher.publish(binding.topic,b'not-json',qos=1).wait_for_publish(5)
            publisher.publish('nodum/unbound',sample('other-topic'),qos=1).wait_for_publish(5)
            wait_for(lambda:subscriber.counts['recorded']==events and subscriber.counts['duplicate']==1 and subscriber.counts['rejected']==2)
            elapsed=time.monotonic()-started
            # Actual broker loss and reconnection, not callback stubs.
            connected.clear()
            broker.terminate();broker.wait(timeout=10);broker=None
            wait_for(lambda:subscriber.status=='disconnected')
            broker=start_broker()
            wait_for(lambda:subscriber.status=='subscribed' and connected.is_set())
            publisher.publish(binding.topic,sample('after-reconnect'),qos=1).wait_for_publish(5)
            wait_for(lambda:subscriber.counts['recorded']==events+1)
            for assignment in repo.list_role_assignments():
                if assignment.user_id==user.id and assignment.role.value=='manager':
                    repo.save_role_assignment(assignment.model_copy(update={'active':False}))
            publisher.publish(binding.topic,sample('after-revocation'),qos=1).wait_for_publish(5)
            wait_for(lambda:subscriber.counts['rejected']==3)
            manager_user=users['demo-manager']
            manager=AuthorizationService(repo,Principal(user_id=manager_user.id,person_id=manager_user.person_id),datetime.now(timezone.utc))
            activity=[e for e in ManagerService(manager).snapshot()['activity'] if e['what']=='sensor contact open']
            recorded=[e for e in repo.list_operational_records('operation_activity') if e.get('source')=='MQTT contact observation']
            if (len(recorded)!=events+1 or len(activity)!=min(events+1,100)
                    or not all(e['simulated'] for e in activity)):
                raise RuntimeError('Scoped activity verification failed')
            if repo.list_actuator_events():raise RuntimeError('Unexpected actuator record')
            return {'protocol':'MQTT 3.1.1 over loopback TCP', 'broker':'aMQTT 0.11.3',
                    'events':events,'elapsed_seconds':round(elapsed,3),'counts':dict(subscriber.counts),
                    'reconnect':'PASS','retained_and_malformed':'rejected','grant_revocation':'PASS',
                    'manager_activity':len(activity),'persisted_observations':len(recorded),
                    'physical_hardware':'not tested','broker_tls_acl':'not tested'}
        finally:
            if subscriber:subscriber.stop()
            if publisher:publisher.disconnect();publisher.loop_stop()
            if broker:broker.terminate();broker.wait(timeout=10)
            os.environ.clear();os.environ.update(previous)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker-python',type=Path,required=True)
    parser.add_argument('--events',type=int,default=3)
    args=parser.parse_args()
    if not args.broker_python.is_file() or not 1<=args.events<=1000:parser.error('Choose an existing broker Python and 1–1000 fixture events')
    print(json.dumps(run(args.broker_python,args.events),indent=2))
