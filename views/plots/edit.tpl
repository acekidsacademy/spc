%include('header')
%include('navbar')

<body>

<script>
function opt() {
  xl = document.getElementById("xaxis_label").value;
  xstr = "xaxis: { axisLabel: \"" + xl + "\"}"
  yl = document.getElementById("yaxis_label").value;
  ystr = "yaxis: { axisLabel: \"" + yl + "\"}"
  // don't set options for categories plot b/c it will not work correctly
  var e = document.getElementById("ptype")
  var strUser = e.options[e.selectedIndex].value;
  if (strUser != "flot-cat") {
    document.getElementById("options").value = 
      "legend: { position: \"nw\"}" + ", " + xstr + ", " + ystr;
  }
}

function leg(val) {
  legpos = document.getElementById("legpos")
  legstr = "legend: { position: \"" + val + "\"}"
  opt()
}

function endis() {
  // disable options for categories plot b/c it will not work correctly
  var e = document.getElementById("ptype")
  var strUser = e.options[e.selectedIndex].value;
  if (strUser == "flot-cat") {
    document.getElementById("options").readOnly = true;
  } else {
    document.getElementById("options").readOnly = false;
  }
}
</script>

<style type="text/css">
  td,th {text-align: center}
</style>

<div class="btn-group">
  <form class="btn-group" method="get" action="/app/{{app}}">
    <button class="btn btn-default"><span class="glyphicon glyphicon-chevron-left"></span> Configure App</button>
    <input type="hidden" name="appname" value="{{app}}">
  </form>
  <button type="button" class="btn btn-default" data-toggle="collapse" 
          data-target="#addplot">Add Plot</button>
</div>

<div class="container-fluid">

<div id="addplot" class="collapse">
<form class="form-horizontal" method="post" action="/plots/create">
    <div class="form-group">
        <label for="title" class="control-label col-md-3">Title:</label>
        <div class="col-md-6"><input type="text" class="form-control" name="title"></div>
    </div>

    <div class="form-group">
        <label for="ptype" class="control-label col-md-3">Type of plot:</label>
        <div class="col-md-6">
            <select name="ptype" id="ptype" class="form-control" onchange="endis()">
                <option VALUE="flot-line">flot/line</option>
                <option VALUE="flot-cat">flot/categories</option>
                <option VALUE="plotly-hist">plotly/histogram</option>
                <option VALUE="mpl-line">matplotlib/line</option>
                <option VALUE="mpl-bar">matplotlib/bar</option>
            </select>
        </div>
    </div>

    <!--
    <fieldset>
      <legend>legend position:</label>
      <input type="radio" name="legpos" value="ne" onclick="leg(this.value)"> ne
      <input type="radio" name="legpos" value="nw" onclick="leg(this.value)"> nw
      <input type="radio" name="legpos" value="se" onclick="leg(this.value)"> se
      <input type="radio" name="legpos" value="sw" onclick="leg(this.value)"> sw
    </fieldset>
    -->

    <label class="control-label">xaxis label:</label>
    <input type="text" class="form-control" name="xaxis_label" id="xaxis_label" onchange="opt()">

    <label class="control-label">yaxis label:</label>
    <input type="text" class="form-control" name="yaxis_label" id="yaxis_label" onchange="opt()">

    <div class="form-group">
        <label for="options" class="control-label col-md-3">Options (JSON):</label>
        <div class="col-md-6">
            <textarea name="options" id="options" class="form-control"></textarea>
        </div>
    </div>

    <input type="submit" class="btn btn-primary" value="Submit">
    <input type="hidden" name="app" value="{{app}}">
    <input type="hidden" name="cid" value="{{cid}}">
</form>
</div>
</div>

<h1 align=center>Plot definitions for {{app}} app</h1>

<table class="table table-striped">
<thead>
<tr>
   <th>id</th>
   <th>Title</th> 
   <th>Type</th> 
   <th>Options</th> 
   <th>Action</th> 
</tr>
</thead>
%for row in rows:
  <tr>
     <td>{{row['plots']['id']}}</td>
     <td>{{row['plots']['title']}}</td>
     <td width="50">{{row['plots']['ptype']}}</td>
     <td>{{row['plots']['options']}}</td>
     <td width="100">
        %if not cid == '':
            <a href="/plot/{{row['plots']['id']}}?app={{app}}&cid={{cid}}">plot</a> <br><br>
        %end
        <a href="/plots/delete/{{row['plots']['id']}}?app={{app}}&cid={{cid}}" 
           onclick="if(confirm('confirm')) return true; return false">delete</a> <br><br>
        <a href="/plots/datasource/{{row['plots']['id']}}?app={{app}}&cid={{cid}}">datasource</a>
     </td>
  </tr> 
%end
</table>

%include('footer')
