from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock


class TaskExecutor:
    """用于在 MVP 模式下模拟异步任务的轻量线程池封装。
    Thin thread-pool wrapper used to simulate asynchronous jobs in MVP mode.
    """

    def __init__(self, max_workers: int) -> None:
        """使用固定数量工作线程初始化执行器。
        Initialize the executor with a bounded worker pool.
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="docfusion")
        self._futures: dict[str, Future[object]] = {}
        self._lock = Lock()

    def submit(self, task_id: str, fn, *args, **kwargs) -> Future[object]:
        """提交可调用对象并将其 Future 与任务 id 关联。
        Submit a callable and associate its future with a task id.
        """
        future = self._executor.submit(fn, *args, **kwargs)
        with self._lock:
            self._futures[task_id] = future
        return future

    def wait(self, task_id: str, timeout: float | None = None) -> object:
        """等待一个已提交任务执行完成。
        Wait for a previously submitted task to finish.
        """
        with self._lock:
            future = self._futures.get(task_id)
        if future is None:
            raise KeyError(f"Unknown task id: {task_id}")
        return future.result(timeout=timeout)

    def shutdown(self) -> None:
        """停止接收新任务并关闭底层线程池。
        Stop accepting work and tear down the backing thread pool.
        """
        self._executor.shutdown(wait=False, cancel_futures=False)
