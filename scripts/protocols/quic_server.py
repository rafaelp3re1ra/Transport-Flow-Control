# Minimal QUIC v1 server: only protocol logic
import asyncio
import os
from aioquic.asyncio import serve
from aioquic.quic.configuration import QuicConfiguration
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.events import StreamDataReceived

class QuicServer(QuicConnectionProtocol):
    def quic_event_received(self, event):
        if isinstance(event, StreamDataReceived):
            size_mb = int(os.environ.get('QUIC_DATA_SIZE_MB', 5))
            with open('/tmp/testfile.bin', 'rb') as f:
                data = f.read(size_mb * 1024 * 1024)
            self._quic.send_stream_data(event.stream_id, data, end_stream=True)

async def run_server():
    configuration = QuicConfiguration(is_client=False)
    configuration.load_cert_chain('/tmp/cert.pem', '/tmp/key.pem')
    await serve(
        '0.0.0.0',
        443,
        configuration=configuration,
        create_protocol=QuicServer,
    )
    await asyncio.Future()  # Run forever

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--run-server':
        asyncio.run(run_server())
