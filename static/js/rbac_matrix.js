// static/js/rbac_matrix.js
$(document).on("change", ".perm-toggle", function () {

    const el = $(this);

    $.ajax({
        url: "/rbac/update-permission/",
        method: "POST",
        data: {
            menu_id: el.data("menu"),
            group_id: el.data("group"),
            perm_type: el.data("type"),
            value: el.is(":checked")
        },
        success: function () {
            console.log("Updated");
        }
    });

});