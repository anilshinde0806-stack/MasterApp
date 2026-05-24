function createERPGrid(gridId, columnDefs, apiUrl) {

    return agGrid.createGrid(
        document.querySelector(gridId),
        {
            rowSelection: "single",

            columnDefs: columnDefs,

            defaultColDef: {
                sortable: true,
                filter: true,
                floatingFilter: true,
                resizable: true,
                editable: true
            },

            pagination: true,
            paginationPageSize: 50,

            animateRows: true
        }
    );
}