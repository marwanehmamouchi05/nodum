"""Opt-in bounded contact telemetry collector. No migration, seed or publication.

Configuration file is private server configuration, never an HTTP payload.
Broker credentials come from MQTT_USERNAME / MQTT_PASSWORD, never CLI arguments.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import ssl
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from pydantic import BaseModel, ConfigDict, Field
from app.config import AppSettings, validate_startup
from app.database import database_path
from app.maintenance import inspect_database
from app.integrations.mqtt_sensor import ContactIngestor, ContactSubscriber, SensorBinding
from app.models.authorization import Principal
from app.services.authorization import AuthorizationService, authorization_mode
from app.sqlite_repository import SQLiteRepository


class CollectorConfig(BaseModel):
    model_config=ConfigDict(extra='forbid')
    host: str=Field(min_length=1,max_length=253)
    port: int=Field(default=8883,ge=1,le=65535,strict=True)
    ca_file: str=Field(min_length=1)
    building_id: str=Field(min_length=1,max_length=256)
    device_id: str=Field(min_length=1,max_length=256)
    operator_user_id: str=Field(min_length=1,max_length=256)
    max_observations: int=Field(default=100000,ge=1,le=1000000,strict=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--seconds',type=int,default=60)
    args=parser.parse_args(argv)
    if not 1<=args.seconds<=3600:parser.error('Observation duration must be 1–3600 seconds')
    subscriber=None
    try:
        settings=AppSettings.from_env()
        validate_startup(settings)
        if settings.environment!='production' or authorization_mode()!='scoped':
            raise ValueError('Requires isolated production/scoped installation')
        inspect_database(database_path())  # No implicit database creation or upgrade.
        config=CollectorConfig.model_validate_json(args.config.read_bytes())
        repo=SQLiteRepository()
        user=repo.get_auth_user(config.operator_user_id)
        if not user:raise ValueError('Operator unavailable')
        def auth():
            return AuthorizationService(repo,Principal(user_id=user.id,person_id=user.person_id),datetime.now(timezone.utc))
        binding=SensorBinding(config.building_id,config.device_id)
        ingestor=ContactIngestor(auth,binding,max_observations=config.max_observations)
        with repo.transaction():
            ingestor.validate_binding(auth())
        context=ssl.create_default_context(cafile=config.ca_file)
        subscriber=ContactSubscriber(ingestor,host=config.host,port=config.port,
            tls_context=context,username=os.getenv('MQTT_USERNAME'),password=os.getenv('MQTT_PASSWORD'))
        subscriber.start()
        deadline=time.monotonic()+args.seconds
        while time.monotonic()<deadline and not subscriber.counts['failed']:
            time.sleep(.1)
        result={'status':subscriber.status,'counts':dict(subscriber.counts)}
        print(json.dumps(result))
        return 0 if subscriber.status=='subscribed' and not subscriber.counts['failed'] else 2
    except Exception:
        # Provider/SSL/file errors may include secrets or private identifiers.
        print(json.dumps({'status':'failed','message':'Check private collector configuration, database, TLS, credentials and operator grants.'}))
        return 2
    finally:
        if subscriber:subscriber.stop()


if __name__=='__main__':
    raise SystemExit(main())
