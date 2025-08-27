from __future__ import annotations

import json
import csv
from dataclasses import dataclass, field, asdict
from typing import Dict

from models import (
    MARKET_PROFILES,
    MarketProfile,
    KitInstance,
    Element,
    DEFAULT_KIT_DEFS,
    PARAM_DEFS,
    apply_market,
)


# Default kit counts based on frozen requirements
DEFAULT_COUNTS = {
    "51": {"51-11": 1, "51-21": 1, "51-31": 0},
    "52": {"52-01": 1, "52-11": 1},
    "53": {"53-11": 1},
    "54": {"54-11": 0},
}


@dataclass
class Estimate:
    project_id: str = ""
    job: str = ""
    title: str = ""
    market_name: str = "Cruise – Large New Build"
    revision: str = "v1.0"
    elements: Dict[str, Element] = field(default_factory=dict)

    def __post_init__(self):
        if not self.elements:
            self.elements = {code: Element(code) for code in DEFAULT_COUNTS.keys() | {"60", "70"}}
            for el_code, kits in DEFAULT_COUNTS.items():
                for kit_code, count in kits.items():
                    for i in range(1, count + 1):
                        defn = DEFAULT_KIT_DEFS[el_code][kit_code]
                        self.elements[el_code].kits.append(KitInstance(defn, i))

    @property
    def market(self) -> MarketProfile:
        return MARKET_PROFILES[self.market_name]

    def to_json(self) -> str:
        data = asdict(self)
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, data: str) -> "Estimate":
        raw = json.loads(data)
        est = cls(
            project_id=raw.get("project_id", ""),
            job=raw.get("job", ""),
            title=raw.get("title", ""),
            market_name=raw.get("market_name", "Cruise – Large New Build"),
            revision=raw.get("revision", "v1.0"),
        )
        est.elements = {}
        for el_code, el_data in raw.get("elements", {}).items():
            element = Element(el_code)
            for kit_data in el_data.get("kits", []):
                kit_code = kit_data["definition"]["code"]
                defn = DEFAULT_KIT_DEFS.get(el_code, {}).get(kit_code)
                if not defn:
                    continue
                kit = KitInstance(defn, kit_data.get("index", 1), kit_data.get("custom_name"))
                kit.param_values = kit_data.get("param_values", {})
                kit.deliverables = kit_data.get("deliverables", 0)
                element.kits.append(kit)
            est.elements[el_code] = element
        return est

    def rollup_totals(self) -> Dict[str, float]:
        totals = {"Dev": 0.0, "Doc": 0.0, "Config": 0.0}
        for code in ["51", "52", "53", "54"]:
            el = self.elements.get(code)
            if not el:
                continue
            seed = el.seed_totals()
            deliverables = sum(k.deliverables for k in el.kits)
            final = apply_market(self.market, seed, deliverables)
            for bucket in totals:
                totals[bucket] += final[bucket]
        return totals

    def export_csv(self, path: str) -> None:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Element",
                    "KitCode",
                    "FinalName",
                    "Dev",
                    "Doc",
                    "Config",
                    "Deliverables",
                ]
            )
            for el_code in ["51", "52", "53", "54", "60", "70"]:
                el = self.elements.get(el_code)
                if not el:
                    continue
                for kit in el.kits:
                    seed = kit.seed_hours()
                    final = apply_market(self.market, seed, kit.deliverables)
                    writer.writerow(
                        [
                            el_code,
                            kit.definition.code,
                            kit.display_name,
                            f"{final['Dev']:.2f}",
                            f"{final['Doc']:.2f}",
                            f"{final['Config']:.2f}",
                            kit.deliverables,
                        ]
                    )
            totals = self.rollup_totals()
            writer.writerow([])
            writer.writerow(["Rollup", "", "", totals["Dev"], totals["Doc"], totals["Config"], ""])
