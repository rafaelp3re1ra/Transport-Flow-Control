# Minimal QUIC v1 client: only protocol logic
import asyncio
import os
import time
from aioquic.asyncio import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived

class ClientQuicProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._received = 0
        self._done = asyncio.Event()
    def quic_event_received(self, event):
        if isinstance(event, StreamDataReceived):
            self._received += len(event.data)
            if event.end_stream:
                self._done.set()

async def run_client(host, duration=30):
    configuration = QuicConfiguration(is_client=True)
    configuration.verify_mode = False
    start_time = time.time()
    results = []
    while time.time() - start_time < duration:
        async with connect(host, 443, configuration=configuration, create_protocol=ClientQuicProtocol) as protocol:
            stream_id = protocol._quic.get_next_available_stream_id()
            protocol._quic.send_stream_data(stream_id, b"GET /data", end_stream=True)
            protocol.transmit()
            await protocol._done.wait()
            results.append(protocol._received)
    return results

async def run_client_parallel(host, duration=30, num_transfers=1):
    async def single_transfer():
        return await run_client(host, duration)
    
    tasks = [single_transfer() for _ in range(num_transfers)]
    all_results = await asyncio.gather(*tasks)
    # Flatten the results
    flattened = [item for sublist in all_results for item in sublist]
    return flattened

if __name__ == "__main__":
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else "quic_server"
    duration = int(os.environ.get('TEST_DURATION', 30))
    num_transfers = int(os.environ.get('QUIC_TRANSFERS', 1))
    res = asyncio.run(run_client_parallel(host, duration, num_transfers))
    print(res)
