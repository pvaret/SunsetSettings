from collections.abc import Callable
import threading

import pytest

from sunset.lock import RWLock


def _start_threaded(target: Callable[[], None]) -> threading.Thread:
    task = threading.Thread(target=target, daemon=True)
    task.start()
    return task


class TestRWLock:
    def test_lock_is_reentrant(self) -> None:
        lock = RWLock()

        def try_lock() -> None:
            with lock.lock_reads():
                with lock.lock_reads():
                    pass

            with lock.lock_writes():
                with lock.lock_writes():
                    pass

            with lock.lock_reads():
                with lock.lock_writes():
                    pass

            with lock.lock_writes():
                with lock.lock_reads():
                    pass

        task = _start_threaded(target=try_lock)
        task.join(timeout=1.0)
        assert not task.is_alive()

    def test_concurrent_readers(self) -> None:
        reader_count = 100
        lock = RWLock()
        read_locks_all_held = threading.Barrier(reader_count + 1)

        def lock_and_wait() -> None:
            with lock.lock_reads():
                read_locks_all_held.wait()

        tasks = [_start_threaded(target=lock_and_wait) for _ in range(reader_count)]

        # This will block unless all threads are at the barrier, which proves that all
        # the readers are holding the read lock.
        assert read_locks_all_held.wait(timeout=1.0)

        [task.join(timeout=1.0) for task in tasks]
        assert all(not task.is_alive() for task in tasks)

    def test_readers_dont_block_readers(self) -> None:
        lock = RWLock()
        lock_acquired = threading.Event()
        testing_done = threading.Event()

        def hold_read_lock() -> None:
            with lock.lock_reads():
                lock_acquired.set()
                testing_done.wait()

        task = _start_threaded(target=hold_read_lock)

        lock_acquired.wait(timeout=1.0)
        assert lock._acquire_read_lock(blocking=False)
        lock._release_read_lock()

        testing_done.set()
        task.join(timeout=1.0)
        assert not task.is_alive()

    def test_writers_block_writers(self) -> None:
        lock = RWLock()
        lock_acquired = threading.Event()
        testing_done = threading.Event()

        def hold_write_lock() -> None:
            with lock.lock_writes():
                lock_acquired.set()
                testing_done.wait()

        task = _start_threaded(target=hold_write_lock)

        lock_acquired.wait(timeout=1.0)
        assert not lock._acquire_write_lock(blocking=False)

        testing_done.set()
        task.join(timeout=1.0)
        assert not task.is_alive()

    def test_readers_block_writers(self) -> None:
        lock = RWLock()
        lock_acquired = threading.Event()
        testing_done = threading.Event()

        def hold_read_lock() -> None:
            with lock.lock_reads():
                lock_acquired.set()
                testing_done.wait()

        task = _start_threaded(target=hold_read_lock)

        lock_acquired.wait(timeout=1.0)
        assert not lock._acquire_write_lock(blocking=False)

        testing_done.set()
        task.join(timeout=1.0)
        assert not task.is_alive()

    def test_writers_block_readers(self) -> None:
        lock = RWLock()
        lock_acquired = threading.Event()
        testing_done = threading.Event()

        def hold_write_lock() -> None:
            with lock.lock_writes():
                lock_acquired.set()
                testing_done.wait()

        task = _start_threaded(target=hold_write_lock)

        lock_acquired.wait(timeout=1.0)
        assert not lock._acquire_read_lock(blocking=False)

        testing_done.set()
        task.join(timeout=1.0)
        assert not task.is_alive()

    def test_readers_dont_starve_writers(self) -> None:
        reader_count = 100
        done = [False]

        lock = RWLock()
        read_locks_all_held = threading.Barrier(parties=reader_count + 1)
        write_lock_acquired = threading.Event()
        writer_can_quit = threading.Event()
        unpause = threading.Semaphore(value=0)

        def hold_read_lock_and_wait() -> None:
            while not done[0]:
                with lock.lock_reads():
                    read_locks_all_held.wait()
                    unpause.acquire()

        def try_write_lock() -> None:
            with lock.lock_writes():
                write_lock_acquired.set()
                writer_can_quit.wait()

        tasks = [_start_threaded(hold_read_lock_and_wait) for _ in range(reader_count)]

        # Ensure that all reader threads are in the locked section. Adding the final
        # waiter to the barrier will unblock the reader threads and they will
        # immediately block on the semaphore on the next line until we unpause it.
        read_locks_all_held.wait()

        # Start the writer. It should not be able to proceed because the reader lock is held.
        tasks.append(_start_threaded(try_write_lock))
        assert not write_lock_acquired.wait(timeout=0.01)
        assert not write_lock_acquired.is_set()

        # But if we let the reader threads proceed...
        unpause.release(reader_count)

        # Then the reader threads should not be able to re-acquire the read lock until
        # the writer waiting on the lock has acquired and then released it.
        assert write_lock_acquired.wait(1.0)

        # And while the writer holds the write lock, no reader should be able to
        # re-enter the critical section.
        assert read_locks_all_held.n_waiting == 0

        # Cleanup is a bit tricky because we need to unpause as many reader threads as
        # are paused. So we let the writer thread terminate and wait until all the
        # reader threads are in the critical section again...
        writer_can_quit.set()
        read_locks_all_held.wait()

        # Then signal that this loop should be the last...
        done[0] = True

        # And then let the reader threads proceed.
        unpause.release(reader_count)

        [task.join(timeout=1.0) for task in tasks]
        assert not any(task.is_alive() for task in tasks)

    def test_releasing_not_held_lock_raises_runtimeerror(self) -> None:
        lock = RWLock()
        lock._acquire_read_lock()
        lock._acquire_read_lock()
        lock._acquire_write_lock()
        lock._acquire_write_lock()

        lock._release_read_lock()
        lock._release_write_lock()
        lock._release_read_lock()
        lock._release_write_lock()

        with pytest.raises(RuntimeError):
            lock._release_read_lock()

        with pytest.raises(RuntimeError):
            lock._release_write_lock()
