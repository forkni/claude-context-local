"""Unit tests for ServiceLocator dependency injection pattern."""

import pytest

from mcp_server.services import ServiceLocator, get_config, get_state


class DummyService:
    """Test service for registration tests."""

    def __init__(self, value: str = "default"):
        self.value = value
        self.initialized = True


class TestServiceLocatorSingleton:
    """Test ServiceLocator singleton pattern."""

    def setup_method(self):
        """Reset ServiceLocator before each test."""
        ServiceLocator.reset()

    def test_instance_returns_singleton(self):
        """Test that instance() returns the same instance across calls."""
        locator1 = ServiceLocator.instance()
        locator2 = ServiceLocator.instance()
        assert locator1 is locator2

    def test_reset_clears_singleton(self):
        """Test that reset() clears the singleton instance."""
        locator1 = ServiceLocator.instance()
        ServiceLocator.reset()
        locator2 = ServiceLocator.instance()
        assert locator1 is not locator2

    def test_new_instance_after_reset_is_clean(self):
        """Test that new instance after reset has no registered services."""
        locator = ServiceLocator.instance()
        locator.register("test", DummyService())

        ServiceLocator.reset()
        new_locator = ServiceLocator.instance()

        assert new_locator.get("test") is None


class TestServiceRegistration:
    """Test service registration patterns."""

    def setup_method(self):
        """Reset ServiceLocator before each test."""
        ServiceLocator.reset()
        self.locator = ServiceLocator.instance()

    def test_register_instance(self):
        """Test registering a service instance."""
        service = DummyService("test_value")
        self.locator.register("dummy", service)

        retrieved = self.locator.get("dummy")
        assert retrieved is service
        assert retrieved.value == "test_value"

    def test_register_multiple_services(self):
        """Test registering multiple different services."""
        service1 = DummyService("value1")
        service2 = DummyService("value2")

        self.locator.register("service1", service1)
        self.locator.register("service2", service2)

        assert self.locator.get("service1").value == "value1"
        assert self.locator.get("service2").value == "value2"

    def test_register_overwrites_existing(self):
        """Test that registering same name overwrites previous service."""
        service1 = DummyService("old")
        service2 = DummyService("new")

        self.locator.register("dummy", service1)
        self.locator.register("dummy", service2)

        retrieved = self.locator.get("dummy")
        assert retrieved is service2
        assert retrieved.value == "new"

    def test_get_unregistered_returns_none(self):
        """Test that getting unregistered service returns None."""
        result = self.locator.get("nonexistent")
        assert result is None


class TestFactoryPattern:
    """Test lazy instantiation via factory registration."""

    def setup_method(self):
        """Reset ServiceLocator before each test."""
        ServiceLocator.reset()
        self.locator = ServiceLocator.instance()
        self.factory_call_count = 0

    def _create_service(self) -> DummyService:
        """Factory function that tracks call count."""
        self.factory_call_count += 1
        return DummyService(f"factory_{self.factory_call_count}")

    def test_register_factory(self):
        """Test registering a factory function."""
        self.locator.register_factory("dummy", self._create_service)

        # Factory not called yet
        assert self.factory_call_count == 0

        # First get() triggers factory
        service = self.locator.get("dummy")
        assert self.factory_call_count == 1
        assert service.value == "factory_1"

    def test_factory_result_is_cached(self):
        """Test that factory is only called once and result is cached."""
        self.locator.register_factory("dummy", self._create_service)

        service1 = self.locator.get("dummy")
        service2 = self.locator.get("dummy")

        # Factory called only once
        assert self.factory_call_count == 1
        # Same instance returned
        assert service1 is service2

    def test_factory_with_lambda(self):
        """Test factory registration with lambda function."""
        self.locator.register_factory("dummy", lambda: DummyService("lambda_value"))

        service = self.locator.get("dummy")
        assert service.value == "lambda_value"

    def test_register_instance_overrides_factory(self):
        """Test that registering instance directly overrides factory."""
        self.locator.register_factory("dummy", self._create_service)

        # Register instance before factory is triggered
        manual_service = DummyService("manual")
        self.locator.register("dummy", manual_service)

        retrieved = self.locator.get("dummy")
        assert retrieved is manual_service
        assert self.factory_call_count == 0  # Factory never called


class TestCacheInvalidation:
    """Test service cache invalidation."""

    def setup_method(self):
        """Reset ServiceLocator before each test."""
        ServiceLocator.reset()
        self.locator = ServiceLocator.instance()

    def test_invalidate_removes_cached_service(self):
        """Test that invalidate removes cached service instance."""
        service = DummyService("original")
        self.locator.register("dummy", service)

        result = self.locator.invalidate("dummy")

        assert result is True
        assert self.locator.get("dummy") is None

    def test_invalidate_with_factory_triggers_recreation(self):
        """Test that invalidate + factory causes re-creation on next get."""
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return DummyService(f"instance_{call_count}")

        self.locator.register_factory("dummy", factory)

        # First access
        service1 = self.locator.get("dummy")
        assert service1.value == "instance_1"
        assert call_count == 1

        # Invalidate and access again
        self.locator.invalidate("dummy")
        service2 = self.locator.get("dummy")

        assert service2.value == "instance_2"
        assert call_count == 2
        assert service1 is not service2

    def test_invalidate_unregistered_returns_false(self):
        """Test that invalidating unregistered service returns False."""
        result = self.locator.invalidate("nonexistent")
        assert result is False

    def test_invalidate_only_affects_target_service(self):
        """Test that invalidate only removes specified service."""
        service1 = DummyService("value1")
        service2 = DummyService("value2")

        self.locator.register("service1", service1)
        self.locator.register("service2", service2)

        self.locator.invalidate("service1")

        assert self.locator.get("service1") is None
        assert self.locator.get("service2") is service2


class TestTypedConvenienceMethods:
    """Test typed convenience methods for common services."""

    def setup_method(self):
        """Reset ServiceLocator before each test."""
        ServiceLocator.reset()
        self.locator = ServiceLocator.instance()

    def test_get_state_with_registered_service(self):
        """Test get_state() returns registered ApplicationState."""
        # Import here to avoid circular dependency issues in test environment
        from mcp_server.state import ApplicationState

        # Create and register state
        state = ApplicationState()
        state.test_marker = "registered"  # Add marker for verification
        self.locator.register("state", state)

        retrieved = self.locator.get_state()
        assert retrieved is state
        assert hasattr(retrieved, "test_marker")
        assert retrieved.test_marker == "registered"

    def test_get_state_auto_creates_if_missing(self):
        """Test get_state() auto-creates ApplicationState if not registered."""
        # Don't register anything
        state = self.locator.get_state()

        # Should return a valid ApplicationState
        assert state is not None
        assert hasattr(state, "current_model_key")  # Check it's ApplicationState

    def test_get_config_with_registered_service(self):
        """Test get_config() returns registered SearchConfig."""
        from search.config import SearchConfig

        # Create and register config
        config = SearchConfig()
        config.test_marker = "registered"  # Add marker for verification
        self.locator.register("config", config)

        retrieved = self.locator.get_config()
        assert retrieved is config
        assert hasattr(retrieved, "test_marker")
        assert retrieved.test_marker == "registered"

    def test_get_config_auto_creates_if_missing(self):
        """Test get_config() auto-creates SearchConfig if not registered."""
        # Don't register anything
        config = self.locator.get_config()

        # Should return a valid SearchConfig
        assert config is not None
        assert hasattr(config, "embedding")  # Check it's SearchConfig

    def test_typed_methods_cache_auto_created_services(self):
        """Test that auto-created services are cached."""
        state1 = self.locator.get_state()
        state2 = self.locator.get_state()

        assert state1 is state2


class TestBackwardCompatibleWrappers:
    """Test backward-compatible wrapper functions."""

    def setup_method(self):
        """Reset ServiceLocator before each test."""
        ServiceLocator.reset()

    def test_get_state_wrapper(self):
        """Test module-level get_state() wrapper function."""
        state = get_state()
        assert state is not None
        assert hasattr(state, "current_model_key")

    def test_get_config_wrapper(self):
        """Test module-level get_config() wrapper function."""
        config = get_config()
        assert config is not None
        assert hasattr(config, "embedding")

    def test_wrappers_use_service_locator(self):
        """Test that wrapper functions use ServiceLocator internally."""
        from mcp_server.state import ApplicationState

        locator = ServiceLocator.instance()
        custom_state = ApplicationState()
        custom_state.test_marker = "custom"
        locator.register("state", custom_state)

        # Wrapper should return the registered service
        state = get_state()
        assert hasattr(state, "test_marker")
        assert state.test_marker == "custom"


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def setup_method(self):
        """Reset ServiceLocator before each test."""
        ServiceLocator.reset()
        self.locator = ServiceLocator.instance()

    def test_service_factory_with_dependencies(self):
        """Test factory that depends on other services."""
        from search.config import SearchConfig

        # Register config first
        config = SearchConfig()
        self.locator.register("config", config)

        # Register factory that uses config
        def create_dependent_service():
            cfg = self.locator.get_config()
            service = DummyService(f"uses_config_{cfg.embedding.model_name}")
            return service

        self.locator.register_factory("dependent", create_dependent_service)

        service = self.locator.get("dependent")
        assert "uses_config_" in service.value

    def test_multiple_factories_independent_instantiation(self):
        """Test that multiple factories are instantiated independently."""
        count_a = 0
        count_b = 0

        def factory_a():
            nonlocal count_a
            count_a += 1
            return DummyService(f"a_{count_a}")

        def factory_b():
            nonlocal count_b
            count_b += 1
            return DummyService(f"b_{count_b}")

        self.locator.register_factory("service_a", factory_a)
        self.locator.register_factory("service_b", factory_b)

        # Access service_a
        self.locator.get("service_a")
        assert count_a == 1
        assert count_b == 0

        # Access service_b
        self.locator.get("service_b")
        assert count_a == 1
        assert count_b == 1

    def test_config_reload_scenario(self):
        """Test invalidation use case: config file reload."""
        config_load_count = 0

        def load_config():
            nonlocal config_load_count
            config_load_count += 1
            from search.config import SearchConfig

            return SearchConfig()

        self.locator.register_factory("config", load_config)

        # Initial load
        config1 = self.locator.get_config()
        assert config_load_count == 1

        # Simulate config file change - invalidate to force reload
        self.locator.invalidate("config")
        config2 = self.locator.get_config()

        assert config_load_count == 2
        assert config1 is not config2


class TestErrorCases:
    """Test error handling and edge cases."""

    def setup_method(self):
        """Reset ServiceLocator before each test."""
        ServiceLocator.reset()
        self.locator = ServiceLocator.instance()

    def test_factory_exception_propagates(self):
        """Test that factory exceptions propagate to caller."""

        def failing_factory():
            raise ValueError("Factory failed")

        self.locator.register_factory("failing", failing_factory)

        with pytest.raises(ValueError, match="Factory failed"):
            self.locator.get("failing")

    def test_none_service_registration(self):
        """Test that None can be registered as a service value."""
        self.locator.register("null_service", None)

        result = self.locator.get("null_service")
        assert result is None

    def test_factory_returning_none(self):
        """Test factory that returns None."""
        self.locator.register_factory("null_factory", lambda: None)

        result = self.locator.get("null_factory")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
