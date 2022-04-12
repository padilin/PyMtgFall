from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type, Union

from loguru import logger


@dataclass
class BulkData:  # ignore[too-many-instance-attributes]
    api_id: str
    uri: str
    type: str
    name: str
    description: str
    download_uri: str
    updated_at: str
    compressed_size: int
    content_type: str
    content_encoding: str
    obj: str


@dataclass
class RelatedCard:  # ignore[too-many-instance-attributes]
    api_id: str
    obj: str
    component: str
    name: str
    type_line: str
    uri: str


@dataclass
class CardFace:  # ignore[too-many-instance-attributes]
    mana_cost: str
    name: str
    obj: str
    artist: Optional[str] = None
    color_indicator: Optional[str] = None
    colors: Optional[str] = None
    cmc: Optional[int] = None
    flavor_text: Optional[str] = None
    illustration_id: Optional[str] = None
    image_uris: Optional[str] = None
    layout: Optional[str] = None
    loyalty: Optional[str] = None
    oracle_id: Optional[str] = None
    oracle_text: Optional[str] = None
    power: Optional[str] = None
    printed_name: Optional[str] = None
    printed_text: Optional[str] = None
    printed_type_line: Optional[str] = None
    toughness: Optional[str] = None
    type_line: Optional[str] = None
    watermark: Optional[str] = None

    # Undocumented
    artist_id: Optional[str] = None
    flavor_name: Optional[str] = None


@dataclass
class Cards:  # ignore[too-many-instance-attributes]
    # Core Card Fields
    api_id: str
    lang: str
    obj: str
    oracle_id: str
    prints_search_uri: str
    rulings_uri: str
    scryfall_uri: str
    uri: str

    # Gameplay Fields
    cmc: int
    color_identity: str
    keywords: List[str]
    layout: str
    legalities: str
    name: str
    oversized: bool
    reserved: bool
    type_line: str

    # Print Fields - unique to particular re/print
    booster: bool
    border_color: str
    # card_back_id: Optional[str] = None
    collector_number: str
    digital: bool
    finishes: List[str]
    frame: str
    full_art: bool
    games: List[str]
    highres_image: bool
    image_status: str
    prices: List[str]
    promo: bool
    # purchase_uris: List[str]
    rarity: str
    related_uris: List[str]
    released_at: str
    reprint: bool
    scryfall_set_uri: str
    set_name: str
    set_search_uri: str
    set_type: str
    set_uri: str
    set: str
    set_id: str
    story_spotlight: bool
    textless: bool
    variation: bool

    # Nullable Core Card Fields
    arena_id: Optional[int] = None
    mtgo_id: Optional[int] = None
    mtgo_foil_id: Optional[int] = None
    multiverse_ids: Optional[List[int]] = None
    tcgplayer_id: Optional[int] = None
    tcgplayer_etched_id: Optional[int] = None
    cardmarket_id: Optional[int] = None

    # Nullable Gameplay Fields
    all_parts: Optional[List[Union[RelatedCard, Dict[str, str]]]] = None
    card_faces: Optional[List[Union[CardFace, Dict[str, str]]]] = None
    color_indicator: Optional[str] = None
    colors: Optional[str] = None
    edhrec_rank: Optional[int] = None
    hand_modifier: Optional[str] = None
    life_modifier: Optional[str] = None
    loyalty: Optional[str] = None
    mana_cost: Optional[str] = None
    oracle_text: Optional[str] = None
    power: Optional[str] = None
    produced_mana: Optional[str] = None
    toughness: Optional[str] = None

    # Nullable Print Fields
    artist: Optional[str] = None
    content_warning: Optional[bool] = None
    flavor_name: Optional[str] = None
    flavor_text: Optional[str] = None
    frame_effects: Optional[List[str]] = None
    illustration_id: Optional[str] = None
    image_uris: Optional[str] = None
    printed_name: Optional[str] = None
    printed_text: Optional[str] = None
    printed_type_line: Optional[str] = None
    promo_types: Optional[List[str]] = None
    variation_of: Optional[str] = None
    security_stamp: Optional[str] = None
    watermark: Optional[str] = None
    preview: Optional[Dict[str, str]] = None

    # Not documented:
    foil: Optional[bool] = None
    nonfoil: Optional[bool] = None
    artist_ids: Optional[List[str]] = None
    card_back_id: Optional[str] = None  # Can be null?
    purchase_uris: List[str] = None  # Can be null?

    def __post_init__(self):
        if self.all_parts:
            returnable = []
            for part in self.all_parts:
                returnable.append(RelatedCard(**part))
            self.all_parts = returnable

        if self.card_faces:
            returnable = []
            for face in self.card_faces:
                returnable.append(CardFace(**face))
            self.card_faces = returnable


@dataclass
class Sets:
    api_id: str
    code: str
    name: str
    set_type: str
    card_count: int
    digital: bool
    foil_only: bool
    nonfoil_only: bool
    scryfall_uri: str
    uri: str
    icon_svg_uri: str
    search_uri: str

    mtgo_code: Optional[str] = None
    tcgplayer_id: Optional[int] = None
    released_at: Optional[str] = None
    block_code: Optional[str] = None
    block: Optional[str] = None
    parent_set_code: Optional[str] = None
    printed_size: Optional[int] = None

    # Undocumented
    arena_code: Optional[str] = None
    obj: Optional[str] = None


@dataclass
class CardSymbols:
    symbol: str
    english: str
    transposable: bool
    represents_mana: bool
    appears_in_mana_costs: bool
    funny: bool
    colors: str
    loose_variant: Optional[str] = None
    cmc: Optional[int] = None
    gatherer_alternates: Optional[List[str]] = None
    svg_uri: Optional[str] = None

    # Undocumented
    obj: str = None


@dataclass
class Rulings:
    source: str
    published_at: str
    comment: str

    # Undocumented
    obj: Optional[str] = None
    oracle_id: Optional[str] = None


@dataclass
class APIList:
    data: List[Dict[str, Any]]

    # Nullable
    has_more: bool = False
    next_page: Optional[str] = None
    total_cards: Optional[int] = None
    warnings: Optional[List[str]] = None

    # Undocumented
    obj: Optional[str] = None
    not_found: Optional[List[str]] = None

    def __post_init__(self):
        temp_data = list()
        logger.debug(f"This is obj processing: {self.obj=}")
        for item in self.data:
            try:
                data_type_class = Object_Map[item["obj"]]
                temp_data.append(data_type_class(**item))
            except TypeError:
                continue
        self.data = temp_data


Object_Map: Dict[str, Type[Cards | CardSymbols | Sets | CardFace | Rulings | RelatedCard | BulkData]] = {
    "set": Sets,
    "list": List,
    "card": Cards,
    "rulings": Rulings,
    "symbology": CardSymbols,
    "": CardFace,
    "": RelatedCard,
    "": BulkData,
}
