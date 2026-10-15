"""Test-only aMQTT broker; refuses non-loopback endpoints. Separate environment."""
import asyncio
import argparse
from amqtt.broker import Broker


async def serve(port):
    broker = Broker({'listeners':{'default':{'type':'tcp','bind':f'127.0.0.1:{port}'}},
                     'plugins':{'amqtt.plugins.authentication.AnonymousAuthPlugin':{'allow_anonymous':True}}})
    await broker.start()
    try:
        await asyncio.Event().wait()
    finally:
        await broker.shutdown()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,required=True)
    args=parser.parse_args()
    if not 1024 <= args.port <= 65535:parser.error('Use an unprivileged local port')
    asyncio.run(serve(args.port))
