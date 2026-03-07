import cocotb
import random
from collections import deque
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Combine


async def reset(dut):
    dut.rst.value = 1
    dut.inp_v.value = 0
    dut.inp_d.value = 0
    dut.out_r.value = 0
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


async def producer(dut, items, timeout_cycles=200):
    """Drive inp_v; waits for inp_r before each write."""
    for item in items:
        waited = 0
        # Always clock once so inp_v=0 takes effect before we reassert
        await RisingEdge(dut.clk)
        while not dut.inp_r.value:
            await RisingEdge(dut.clk)
            waited += 1
            if waited > timeout_cycles:
                raise TimeoutError(
                    f"Producer timed out waiting for inp_r at item {item}"
                )
        dut.inp_d.value = item
        dut.inp_v.value = 1
        await RisingEdge(dut.clk)
        dut.inp_v.value = 0


async def consumer(dut, count, timeout_cycles=200):
    """Drive out_r; waits for out_v before each read. Returns list of received values."""
    received = []
    for _ in range(count):
        waited = 0
        # Always clock once so out_r=0 takes effect before we reassert
        await RisingEdge(dut.clk)
        while not dut.out_v.value:
            await RisingEdge(dut.clk)
            waited += 1
            if waited > timeout_cycles:
                raise TimeoutError(
                    f"Consumer timed out waiting for out_v after {len(received)} reads"
                )
        dut.out_r.value = 1
        received.append(int(dut.out_d.value))
        await RisingEdge(dut.clk)
        dut.out_r.value = 0
    return received


@cocotb.test()
async def test_burst_then_drain(dut):
    """Write BURST items with no concurrent consumer, then read them back in order.

    Fails with DEPTH=4: producer blocks at item 5 waiting for !full → timeout.
    Passes with DEPTH=8.
    """
    BURST = 8
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)

    items = list(range(BURST))
    await producer(dut, items, timeout_cycles=50)

    received = await consumer(dut, BURST, timeout_cycles=50)
    assert received == items, f"Expected {items}, got {received}"


@cocotb.test()
async def test_concurrent(dut):
    """Concurrent producer and consumer; 16 items flow through."""
    COUNT = 16
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)

    items = list(range(COUNT))
    prod = cocotb.start_soon(producer(dut, items, timeout_cycles=500))
    received = await consumer(dut, COUNT, timeout_cycles=500)
    await prod

    assert received == items, f"Expected {items}, got {received}"


@cocotb.test()
async def test_full_throughput(dut):
    """Producer and consumer both active every cycle; expect 1 transaction/cycle."""
    COUNT = 32
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)

    received = []

    async def driving_producer():
        dut.inp_v.value = 1
        for item in range(COUNT):
            while not dut.inp_r.value:
                await RisingEdge(dut.clk)
            dut.inp_d.value = item
            await RisingEdge(dut.clk)
        dut.inp_v.value = 0

    async def driving_consumer():
        dut.out_r.value = 1
        for _ in range(COUNT):
            while not dut.out_v.value:
                await RisingEdge(dut.clk)
            received.append(int(dut.out_d.value))  # sample before clock
            await RisingEdge(dut.clk)  # head advances here
        dut.out_r.value = 0

    prod = cocotb.start_soon(driving_producer())
    await driving_consumer()
    await prod

    assert received == list(range(COUNT)), (
        f"Expected {list(range(COUNT))}, got {received}"
    )


@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def test_slow_consumer(dut):
    """Producer runs at full speed; consumer reads every other cycle.
    FIFO fills up, inp_r goes low, producer stalls; no data loss."""
    COUNT = 32
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)

    received = []

    async def driving_producer():
        dut.inp_v.value = 1
        for item in range(COUNT):
            while not dut.inp_r.value:
                await RisingEdge(dut.clk)
            dut.inp_d.value = item
            await RisingEdge(dut.clk)
        dut.inp_v.value = 0

    async def slow_consumer():
        for _ in range(COUNT):
            while not dut.out_v.value:
                await RisingEdge(dut.clk)
            dut.out_r.value = 1
            received.append(int(dut.out_d.value))
            await RisingEdge(dut.clk)
            dut.out_r.value = 0
            await RisingEdge(dut.clk)  # idle cycle

    prod = cocotb.start_soon(driving_producer())
    await slow_consumer()
    await prod

    assert received == list(range(COUNT)), (
        f"Expected {list(range(COUNT))}, got {received}"
    )


@cocotb.test()
async def test_slow_producer(dut):
    """Consumer runs at full speed; producer writes every other cycle.
    FIFO drains intermittently, out_v goes low, consumer stalls; no data loss."""
    COUNT = 32
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)

    received = []

    async def slow_producer():
        dut.inp_v.value = 1
        for item in range(COUNT):
            while not dut.inp_r.value:
                await RisingEdge(dut.clk)
            dut.inp_d.value = item
            await RisingEdge(dut.clk)
            dut.inp_v.value = 0
            await RisingEdge(dut.clk)  # idle cycle
            dut.inp_v.value = 1
        dut.inp_v.value = 0

    async def driving_consumer():
        dut.out_r.value = 1
        for _ in range(COUNT):
            while not dut.out_v.value:
                await RisingEdge(dut.clk)
            received.append(int(dut.out_d.value))
            await RisingEdge(dut.clk)
        dut.out_r.value = 0

    prod = cocotb.start_soon(slow_producer())
    await driving_consumer()
    await prod

    assert received == list(range(COUNT)), (
        f"Expected {list(range(COUNT))}, got {received}"
    )


@cocotb.test()
async def test_backpressure(dut):
    """Producer sends 8 items; consumer starts 6 cycles late; no data loss."""
    COUNT = 8
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)

    items = list(range(COUNT))

    async def delayed_consumer():
        for _ in range(6):
            await RisingEdge(dut.clk)
        return await consumer(dut, COUNT, timeout_cycles=500)

    prod = cocotb.start_soon(producer(dut, items, timeout_cycles=500))
    received = await delayed_consumer()
    await prod

    assert received == items, f"Expected {items}, got {received}"


@cocotb.test()
async def test_random_traffic(dut):
    """Random valid/ready each cycle; deque reference model verifies ordering."""
    rnd = random.Random(42)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Reset (drive on falling edge like the reference)
    await FallingEdge(dut.clk)
    dut.rst.value = 1
    dut.inp_v.value = 0
    dut.inp_d.value = 0
    dut.out_r.value = 0
    await FallingEdge(dut.clk)
    dut.rst.value = 0
    await FallingEdge(dut.clk)

    q = deque()
    inp_index = 0

    def gen_examples(n=1000):
        for _ in range(n):
            yield rnd.uniform(0, 1) < 0.85, rnd.uniform(0, 1) < 0.85

    for g_i, g_o in gen_examples():

        async def sample_inp(g_i=g_i):
            nonlocal inp_index
            data = inp_index % 256
            dut.inp_v.value = 1 if g_i else 0
            dut.inp_d.value = data
            # Capture inp_r BEFORE clock (FWFT: inp_r is combinatorial)
            inp_ready = bool(dut.inp_r.value)
            await RisingEdge(dut.clk)
            if g_i and inp_ready:
                q.append(data)
                inp_index += 1
            await FallingEdge(dut.clk)

        async def sample_out(g_o=g_o):
            dut.out_r.value = 1 if g_o else 0
            # Capture out_v and out_d BEFORE clock (FWFT: both combinatorial)
            out_valid = bool(dut.out_v.value)
            out_data = int(dut.out_d.value)
            await RisingEdge(dut.clk)
            if out_valid and g_o:
                expected = q.popleft()
                assert out_data == expected, f"Got {out_data}, expected {expected}"
            await FallingEdge(dut.clk)

        await Combine(
            cocotb.start_soon(sample_inp()),
            cocotb.start_soon(sample_out()),
        )
