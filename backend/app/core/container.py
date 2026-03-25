from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.parsers.factory import ParserRegistry
from app.repositories.memory import InMemoryRepository
from app.services.agent_service import AgentService
from app.services.document_service import DocumentService
from app.services.fact_extraction import FactExtractionService
from app.services.template_service import TemplateService
from app.services.trace_service import TraceService
from app.tasks.executor import TaskExecutor


@dataclass(slots=True)
class ServiceContainer:
    """聚合核心服务，供 API 处理函数共享单例依赖图。
    Bundle all core services so API handlers can share one singleton graph.
    """

    settings: Settings
    repository: InMemoryRepository
    executor: TaskExecutor
    parser_registry: ParserRegistry
    extraction_service: FactExtractionService
    document_service: DocumentService
    template_service: TemplateService
    trace_service: TraceService
    agent_service: AgentService


@lru_cache(maxsize=1)
def get_container() -> ServiceContainer:
    """创建并缓存应用级服务容器。
    Create and cache the application service container.
    """
    settings = get_settings()
    repository = InMemoryRepository()
    executor = TaskExecutor(max_workers=settings.max_workers)
    parser_registry = ParserRegistry()
    extraction_service = FactExtractionService()
    document_service = DocumentService(
        repository=repository,
        parser_registry=parser_registry,
        extraction_service=extraction_service,
        executor=executor,
        settings=settings,
    )
    template_service = TemplateService(
        repository=repository,
        executor=executor,
        settings=settings,
    )
    trace_service = TraceService(repository=repository)
    agent_service = AgentService(repository=repository)
    return ServiceContainer(
        settings=settings,
        repository=repository,
        executor=executor,
        parser_registry=parser_registry,
        extraction_service=extraction_service,
        document_service=document_service,
        template_service=template_service,
        trace_service=trace_service,
        agent_service=agent_service,
    )
