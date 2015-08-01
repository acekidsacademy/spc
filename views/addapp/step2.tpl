<!DOCTYPE html>
<html>
<head>
<link rel="Stylesheet" href="/static/bootstrap/css/bootstrap.min.css" />
</head>
<body>

<div class="container-fluid">
<h1>Step 2</h1>

<h2>Upload zip file</h2>

<font size="+1">
<p>Upload a Zip file named <b><tt>{{appname}}.zip</tt></b>,
which contains the following files:</p>
<ol>
%if input_format == "namelist":
    <li> an input file named <b><tt>{{appname}}.in</tt></b>
%else:
    <li> an input file named <b><tt>{{appname}}.ini</tt></b>
%end
<li> an executable file called <b><tt>{{appname}}</tt></b>, 
     along  with any necessary supporting files 
</ol>

<p>Your app must be able to read and parse a text input file with
the input parameters.</p>
</font>

<form action="/addapp/step3" method="post" enctype="multipart/form-data">
  <!-- Category: <input type="text" name="category" /> -->
  <font size="+1">Select a zip file:</font> 
  <input type="file" name="upload"><br>
  <input type="hidden" name="appname" value="{{appname}}">
  <input type="hidden" name="input_format" value="{{input_format}}">
  <input type="submit" value="Next >>" class="btn btn-primary"/>
</form>
</div>

%include('footer')
