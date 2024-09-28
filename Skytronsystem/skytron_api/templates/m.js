map = new ol.Map({
    target: 'map',
    layers: [


        new ol.layer.Tile({
            source: new ol.source.XYZ({
                url: 'https://bhuvan-ras2.nrsc.gov.in/tilecache/tilecache.py/1.1.1/bhuvan_imagery2/{z}/{x}/{y}.png'
            })
        }),
     
        //indiabasemap 
        new ol.layer.Tile({
            source: new ol.source.TileWMS({
                url: 'https://bhuvan-vec1.nrsc.gov.in/bhuvan/gwc/service/wms',
                params: {
                    'LAYERS': 'basemap%3Aadmin_group',
                    'TILED': true,
                    'VERSION': '1.1.1',
                    'FORMAT': 'image/png',
                    'TRANSPARENT': 'true',
                    'SRS': 'EPSG:4326',
                    'WIDTH': 256,   // Set the tile width to 256 pixels
                    'HEIGHT': 256,   // Set the tile height to 256 pixels
                    'pixelRatio': 1,

                },
                serverType: 'geoserver',
                projection: 'EPSG:4326', // Ensure the projection is set:' 



            })
        }),
        //Road etc 
        new ol.layer.Tile({
            source: new ol.source.TileWMS({
                url: 'https://bhuvan-vec1.nrsc.gov.in/bhuvan/gwc/service/wms',
                params: {
                    'LAYERS': 'mmi:mmi_india',
                    'TILED': true,
                    'VERSION': '1.1.1',
                    'FORMAT': 'image/png',
                    'TRANSPARENT': 'true',
                    'SRS': 'EPSG:4326',
                    'WIDTH': 256,   // Set the tile width to 256 pixels
                    'HEIGHT': 256,   // Set the tile height to 256 pixels
                    'pixelRatio': 1,

                },
                serverType: 'geoserver',
                projection: 'EPSG:4326', // Ensure the projection is set:' 



            })
        })


    ],
    view: new ol.View({
        center: ol.proj.fromLonLat([91.829437, 26.131644]),
        zoom: 7,
    }),

    pixelRatio: 1,
});
