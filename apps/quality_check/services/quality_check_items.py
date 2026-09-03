from core.models import QualityCheckItem

QUALITY_CHECK_ITEMS = [
    {
        "item_key": "paint_finish",
        "item_name": "Paint Finish",
        "category": "Body and Paint",
    },
    {
        "item_key": "color_match",
        "item_name": "Color Match",
        "category": "Body and Paint",
    },
    {
        "item_key": "panel_alignment",
        "item_name": "Panel Alignment",
        "category": "Body and Paint",
    },
    {
        "item_key": "electrical_check",
        "item_name": "Electrical Check",
        "category": "Mechanical and Electrical",
    },
    {
        "item_key": "ac_check",
        "item_name": "AC Check",
        "category": "Mechanical and Electrical",
    },
    {
        "item_key": "road_test",
        "item_name": "Road Test",
        "category": "Mechanical and Electrical",
    },
    {
        "item_key": "washing_done",
        "item_name": "Washing Done",
        "category": "Cleaning",
    },
    {
        "item_key": "interior_cleaning",
        "item_name": "Interior Cleaning",
        "category": "Cleaning",
    },
    {
        "item_key": "exterior_cleaning",
        "item_name": "Exterior Cleaning",
        "category": "Cleaning",
    },
    {
        "item_key": "tool_kit_available",
        "item_name": "Tool Kit Available",
        "category": "Vehicle Items",
    },
    {
        "item_key": "spare_wheel_available",
        "item_name": "Spare Wheel Available",
        "category": "Vehicle Items",
    },
    {
        "item_key": "fuel_level_checked",
        "item_name": "Fuel Level Checked",
        "category": "Vehicle Items",
    },
    {
        "item_key": "customer_belongings_checked",
        "item_name": "Customer Belongings Checked",
        "category": "Vehicle Items",
    },
    {
        "item_key": "documents_checked",
        "item_name": "Documents Checked",
        "category": "Vehicle Items",
    },
    {
        "item_key": "final_inspection",
        "item_name": "Final Inspection",
        "category": "Final Inspection",
    },
]

def ensure_quality_check_items(quality_check):


    existing_keys = set(
        quality_check.items.values_list(
            "item_key",
            flat=True,
        )
    )

    items_to_create = []

    for item in QUALITY_CHECK_ITEMS:
        if item["item_key"] not in existing_keys:
            items_to_create.append(
                QualityCheckItem(
                    quality_check=quality_check,
                    item_key=item["item_key"],
                    item_name=item["item_name"],
                    category=item["category"],
                    status=QualityCheckItem.Status.PENDING,
                )
            )

    if items_to_create:
        QualityCheckItem.objects.bulk_create(
            items_to_create,
        )

    return quality_check.items.all()