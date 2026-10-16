from app.llm.router import model_catalog, route


def test_extraction_uses_cheap_tier(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "fallback/model")
    monkeypatch.setenv("MODEL_CHEAP", "cheap/model")
    decision = route("extraction", "classify this ticket")
    assert decision.tier == "cheap"
    assert decision.model == "cheap/model"


def test_normal_chat_uses_balanced_tier(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "fallback/model")
    monkeypatch.setenv("MODEL_BALANCED", "balanced/model")
    decision = route("chat", "Hello, how are you?")
    assert decision.tier == "balanced"
    assert decision.model == "balanced/model"


def test_complex_chat_uses_powerful_tier(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "fallback/model")
    monkeypatch.setenv("MODEL_POWERFUL", "powerful/model")
    decision = route(
        "chat",
        "Analyze this system design and compare the architecture trade-offs.",
    )
    assert decision.tier == "powerful"
    assert decision.model == "powerful/model"


def test_router_falls_back_to_existing_model(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "existing/model")
    monkeypatch.delenv("MODEL_CHEAP", raising=False)
    decision = route("classification", "billing")
    assert decision.model == "existing/model"


def test_main_tier_pins_to_model_name(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "main/model")
    monkeypatch.setenv("MODEL_CHEAP", "cheap/model")
    decision = route("chat", "debug this architecture tradeoff", force_tier="main")
    assert decision.tier == "main"
    assert decision.model == "main/model"
    assert decision.reason == "tier pinned by request"


def test_catalog_lists_main_first_with_model_name(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "main/model")
    monkeypatch.delenv("MODEL_CHEAP", raising=False)
    catalog = model_catalog()
    assert [entry["tier"] for entry in catalog] == [
        "main",
        "cheap",
        "balanced",
        "powerful",
        "openai-compatible",
    ]
    main = catalog[0]
    assert main["model"] == "main/model"
    assert main["env_var"] == "MODEL_NAME"
    assert main["configured"] is True
    # cheap is unset, so it falls back to MODEL_NAME and is flagged as fallback.
    assert catalog[1]["model"] == "main/model"
    assert catalog[1]["fallback"] is True


def test_openai_compatible_tier_resolves_to_openai_slot(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "main/model")
    monkeypatch.setenv("OPENAI_MODEL", "gemini-2.5-flash")
    decision = route("chat", "hello", force_tier="openai-compatible")
    assert decision.tier == "openai-compatible"
    assert decision.model == "gemini-2.5-flash"
    assert decision.reason == "tier pinned by request"


def test_openai_compatible_falls_back_to_model_name(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "main/model")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    decision = route("chat", "hello", force_tier="openai-compatible")
    assert decision.model == "main/model"


def test_openai_compatible_catalog_entry_reports_its_env_var(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "main/model")
    monkeypatch.setenv("OPENAI_MODEL", "gemini-2.5-flash")
    catalog = [
        entry for entry in model_catalog() if entry["tier"] == "openai-compatible"
    ]
    assert catalog[0]["model"] == "gemini-2.5-flash"
    assert catalog[0]["env_var"] == "OPENAI_MODEL"
    assert catalog[0]["configured"] is True
