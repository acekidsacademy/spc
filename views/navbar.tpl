<div class="navbar">
<a href="/" border=0>
   <img align="right" height="43" src="/static/scipaas.png"/>
</a>
<form id="plotform" action="/{{app}}" method="post">
<input type="text" class="cid" name="cid" id="cid" value="{{cid}}"/>
<input type="submit" formaction="/{{app}}/start" class="start" value="start"/>
<input type="submit" formaction="/{{app}}/{{cid}}/plot" class="plot" value="plot"/>
<input type="submit" formaction="/{{app}}/list" class="list" value="list"/>
<input type="submit" formaction="/{{app}}/{{cid}}/output" class="output" value="output"/>
</form>
<label style="position: absolute; left: 550; color: white;">user: {{user}}</label>

</div>

