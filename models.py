from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any


@dataclass
class MarketProfile:
    name: str
    eng_multiplier: float
    doc_hours_per_deliverable: float
    documentation_multiplier: float
    pm_overhead_multiplier: float


MARKET_PROFILES: Dict[str, MarketProfile] = {
    "Cruise – Large New Build": MarketProfile(
        name="Cruise – Large New Build",
        eng_multiplier=1.10,
        doc_hours_per_deliverable=3.0,
        documentation_multiplier=1.20,
        pm_overhead_multiplier=1.10,
    ),
    "Cruise – Small Controls/Safety Upgrade": MarketProfile(
        name="Cruise – Small Controls/Safety Upgrade",
        eng_multiplier=0.95,
        doc_hours_per_deliverable=0.5,
        documentation_multiplier=0.75,
        pm_overhead_multiplier=0.95,
    ),
    "High-Documentation Rigor Client": MarketProfile(
        name="High-Documentation Rigor Client",
        eng_multiplier=1.20,
        doc_hours_per_deliverable=10.0,
        documentation_multiplier=1.30,
        pm_overhead_multiplier=1.20,
    ),
}


@dataclass
class KitDefinition:
    code: str
    default_name: str
    formula: Optional[Callable[[Dict[str, Any]], Dict[str, float]]] = None

    def compute_seed_hours(self, values: Dict[str, Any]) -> Dict[str, float]:
        if self.formula:
            return self.formula(values)
        return {"Dev": 0.0, "Doc": 0.0, "Config": 0.0}


@dataclass
class KitInstance:
    definition: KitDefinition
    index: int
    custom_name: Optional[str] = None
    param_values: Dict[str, Any] = field(default_factory=dict)
    deliverables: int = 0

    @property
    def display_name(self) -> str:
        base = f"{self.definition.code}-{self.index:02d}"
        name = self.custom_name or self.definition.default_name
        return f"{base} {name}"

    def seed_hours(self) -> Dict[str, float]:
        return self.definition.compute_seed_hours(self.param_values)


@dataclass
class Element:
    code: str
    kits: List[KitInstance] = field(default_factory=list)
    notes: str = ""

    def seed_totals(self) -> Dict[str, float]:
        totals = {"Dev": 0.0, "Doc": 0.0, "Config": 0.0}
        for kit in self.kits:
            hours = kit.seed_hours()
            for bucket in totals:
                totals[bucket] += hours.get(bucket, 0.0)
        return totals


def apply_market(profile: MarketProfile, seed: Dict[str, float], deliverables: int) -> Dict[str, float]:
    dev = seed["Dev"] * profile.eng_multiplier * profile.pm_overhead_multiplier
    doc = deliverables * profile.doc_hours_per_deliverable * profile.documentation_multiplier
    config = seed["Config"]
    return {"Dev": dev, "Doc": doc, "Config": config}


def mcc_type1_formula(values: Dict[str, Any]) -> Dict[str, float]:
    axes_total = values.get("axes_total", 0)
    axes_complex = values.get("axes_complex", 0)
    is_legacy = values.get("is_legacy_mcc", False)
    config = 3.0 * axes_total + 2.0 * axes_complex + (1.5 * axes_total if is_legacy else 0) + 2.0
    dev = 0.75 * axes_complex + (0.5 * axes_total if is_legacy else 0)
    doc = 0.1 * axes_total
    return {"Config": config, "Dev": dev, "Doc": doc}


DEFAULT_KIT_DEFS: Dict[str, Dict[str, KitDefinition]] = {
    "51": {
        "51-11": KitDefinition("51-11", "Consoles & HMIs"),
        "51-21": KitDefinition("51-21", "Control/Nav/E-Stops"),
        "51-31": KitDefinition("51-31", "Pendants"),
    },
    "52": {
        "52-01": KitDefinition("52-01", "Rack Build"),
        "52-11": KitDefinition("52-11", "MCR"),
    },
    "53": {
        "53-11": KitDefinition("53-11", "MCC Type 1", formula=mcc_type1_formula),
    },
    "54": {
        "54-11": KitDefinition("54-11", "Kit A"),
    },
}

# Parameter definitions for dynamic forms
PARAM_DEFS: Dict[str, Dict[str, type]] = {
    "51-11": {
        "hmi_pages": int,
        "alarms": int,
        "trends": int,
        "security_roles": int,
    },
    "51-21": {
        "nav_points": int,
        "e_stops": int,
        "interlocks": int,
    },
    "51-31": {
        "axes_controlled": int,
    },
    "52-01": {
        "rack_units": int,
        "power_zones": int,
        "network_switches": int,
        "ethercat_nodes": int,
    },
    "52-11": {
        "ethercat_nodes": int,
        "net_segments": int,
        "uplinks": int,
    },
    "53-11": {
        "axes_total": int,
        "axes_complex": int,
        "is_legacy_mcc": bool,
    },
    "54-11": {
        "custom_factor": float,
        "io_points": int,
        "safety_devices": int,
    },
}
