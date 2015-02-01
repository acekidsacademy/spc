<html>
<head>
    <script type="text/javascript" src="/static/js/main.js" charset="utf-8"></script>
    <script type="text/javascript" src="/static/js/tabpane.js"></script>

    <script type="text/javascript" src="/static/js/tablesorter/jquery-latest.js"></script>
    <script type="text/javascript" src="/static/js/tablesorter/jquery.tablesorter.js"></script>

    <link rel="stylesheet" href="/static/css/jq.css" type="text/css" media="print, projection, screen" />
    <link rel="stylesheet" href="/static/js/tablesorter/style.css" type="text/css" media="print, projection, screen" />

    <link type="text/css" rel="StyleSheet" href="/static/css/default.css" />
    <link type="text/css" rel="StyleSheet" href="/static/css/exe.css" />
    <link type="text/css" rel="StyleSheet" href="/static/css/tab.webfx.css"/>
    <link type="text/css" rel="StyleSheet" href="/static/css/dropdown.css"/>

    <title>SciPaaS</title>
    <script type="text/javascript">
    setupAllTabs();
    </script>
    <script type="text/javascript">
     $(function() {
        $("#tablesorter").tablesorter({sortList:[[0,1]], widgets: ['zebra']});
        $("#options").tablesorter({sortList: [[0,0]], headers: { 3:{sorter: false}, 4:{sorter: false}}});
     });
    </script>
</head>
