%include('header')
%include('navbar')

<h1>{{app}} app</h1>

<div class="container-fluid">
<form role="form" class="form-horizontal" method="post" action="/app/save/{{rows['id']}}">

<table>
  </tr>
  <!-- <tr>
      <td>Category:</td>
      <td><input class="form-control" type="text" name="category"
                 value="{{rows['category']}}"></td>
  </tr> -->
  <tr>
      <td>Description:</th>
      <td><textarea class="form-control" name="description" cols="60" rows="4">{{rows['description']}}</textarea></td>
  </tr>
  <tr>
      <td>Input format:</td>
      <td><select class="form-control" name="input_format">
          %opts = {'namelist':'namelist.input','ini':'INI file','xml':'XML file'}
          %for key, value in opts.iteritems():
              %if key == rows['input_format']:
                  <option selected value="{{key}}">{{value}}
              %else:
                  <option value="{{key}}">{{value}}
              %end
          %end
      </select>
      </td>
  </tr>
  <!-- <tr>
      <td>Language:</td>
      <td><input class="form-control" type="text" name="language" 
                 value="{{rows['language']}}"></td> 
  </tr> -->
  <tr>
      <td>Command:</td> 
      <td><input class="form-control" type="text" name="command" size="40"
                 value="{{rows['command']}}"></td> 
  </tr>
</table>
<div class="row">
    <div class="col-md-12 col-md-offset-2">
        <input type="hidden" name="app" value="{{rows['name']}}">
        <input type="submit" class="btn btn-success" value="save changes">
        <a href="/app/{{app}}">
            <input type="button" class="btn btn-default" value="cancel">
        </a>
    </div>
</div>
</form>
</div>

%include('footer')
