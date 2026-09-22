from core.models import QualityCheckItem

QUALITY_CHECK_ITEMS = [
    # category_order, category, item_order, item_key, item_name

    # 1. Exterior
    (1, "Exterior", 1, "body_panel_alignment", "Body Panel Alignment"),
    (1, "Exterior", 2, "paint_finish", "Paint Finish"),
    (1, "Exterior", 3, "bumper_condition", "Bumper Condition"),
    (1, "Exterior", 4, "door_alignment", "Door Alignment"),
    (1, "Exterior", 5, "lights_indicators", "Lights & Indicators"),
    (1, "Exterior", 6, "glass_windshield", "Glass & Windshield"),

    # 2. Paint & Body
    (2, "Paint & Body", 1, "paint_match", "Paint Match"),
    (2, "Paint & Body", 2, "surface_finish", "Surface Finish"),
    (2, "Paint & Body", 3, "no_dents_scratches", "No Dents / Scratches"),
    (2, "Paint & Body", 4, "underbody_coating", "Underbody Coating"),
    (2, "Paint & Body", 5, "rust_protection", "Rust Protection"),

    # 3. Interior
    (3, "Interior", 1, "dashboard", "Dashboard"),
    (3, "Interior", 2, "seats_upholstery", "Seats & Upholstery"),
    (3, "Interior", 3, "floor_mats", "Floor Mats"),
    (3, "Interior", 4, "ac_climate_control", "AC / Climate Control"),
    (3, "Interior", 5, "infotainment_system", "Infotainment System"),
    (3, "Interior", 6, "interior_lights", "Interior Lights"),

    # 4. Electrical
    (4, "Electrical", 1, "headlights_taillights", "Headlights / Taillights"),
    (4, "Electrical", 2, "indicators_horn", "Indicators / Horn"),
    (4, "Electrical", 3, "wipers", "Wipers"),
    (4, "Electrical", 4, "battery", "Battery"),
    (4, "Electrical", 5, "charging_system", "Charging System"),

    # 5. Mechanical
    (5, "Mechanical", 1, "brakes", "Brakes"),
    (5, "Mechanical", 2, "engine_performance", "Engine Performance"),
    (5, "Mechanical", 3, "tyre_condition", "Tyre Condition"),
    (5, "Mechanical", 4, "steering", "Steering"),
    (5, "Mechanical", 5, "suspension", "Suspension"),
    (5, "Mechanical", 6, "fluid_levels", "Fluid Levels"),

    # 6. Safety
    (6, "Safety", 1, "seat_belts", "Seat Belts"),
    (6, "Safety", 2, "airbags", "Airbags"),
    (6, "Safety", 3, "abs", "ABS"),
    (6, "Safety", 4, "esc_traction_control", "ESC / Traction Control"),
    (6, "Safety", 5, "fire_extinguisher", "Fire Extinguisher"),

    # 7. Road Test
    (7, "Road Test", 1, "steering_response", "Steering Response"),
    (7, "Road Test", 2, "braking_performance", "Braking Performance"),
    (7, "Road Test", 3, "acceleration", "Acceleration"),
    (7, "Road Test", 4, "noise_vibration", "Noise / Vibration"),
    (7, "Road Test", 5, "overall_driving", "Overall Driving"),

    # 8. Documents & Accessories
    (8, "Documents & Accessories", 1, "rc_book", "RC Book"),
    (8, "Documents & Accessories", 2, "insurance_copy", "Insurance Copy"),
    (8, "Documents & Accessories", 3, "service_history", "Service History"),
    (8, "Documents & Accessories", 4, "spare_wheel_tools", "Spare Wheel & Tools"),
    (8, "Documents & Accessories", 5, "owner_manual", "Owner Manual"),
]

def ensure_quality_check_items(quality_check):
    existing_keys = set(
        quality_check.items.values_list(
            "item_key",
            flat=True,
        )
    )

    items_to_create = []

    for (
        category_order,
        category,
        item_order,
        item_key,
        item_name,
    ) in QUALITY_CHECK_ITEMS:

        if item_key not in existing_keys:
            items_to_create.append(
                QualityCheckItem(
                    quality_check=quality_check,
                    item_key=item_key,
                    item_name=item_name,
                    category=category,
                    category_order=category_order,
                    item_order=item_order,
                    status=QualityCheckItem.Status.PENDING,
                )
            )

    if items_to_create:
        QualityCheckItem.objects.bulk_create(
            items_to_create,
        )

    return quality_check.items.all()