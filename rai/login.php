<?php

require_once('modules/session.php');
require_once('modules/configuration.php');
$sess = new Session(true);
$site = new Configuration();
$info = $site->getSite();
	
if(isset($_POST['access']) && !isset($error_txt)) {
	if ($sess->access->login($_POST['username'],$_POST['password'],$_POST['language'])) {
		return;
	}
}

require_once('include/header.php');

?>
	<script type="text/javascript" src="js/jquery.ddslick.js"></script>
	<script>
	$( document ).ready(function() {
		$('#language-select').ddslick({
			width: 200,
			onSelected: function(data){
				$('#language').val(data.selectedData.value);
			}
			
		});	
	});		

	</script>
	<br/><br/><br/><br/>

<?php
	function print_form($post_data, $errors, $language) {
		global $langcode, $info;
		$username = (isset($_POST['username'])) ? $_POST['username'] : '';
		$password = (isset($_POST['password'])) ? $_POST['password'] : '';
		$_code = array("es"=>'',"en"=>'');
		$lcl_icon_file = 'img/'.$language."_".$langcode."_flag.png";
		if (file_exists($lcl_icon_file)) {
			$_code[$language] = "_".$langcode;
		}
?>
<form action="login.php" method="post" id="newRequestForm">
<fieldset class="formLogin">
    <h2><?= $info->site_name ?> - <?= $info->network_name ?></h2>
    <div style='margin:auto; width:130px; color: red; font-size: 12px;'><?= nl2br($errors) ?></div><br/>
    <div>
        <label for="user_login"><?=_('Username:')?> &nbsp;</label>
	<input type='text' name='username' size='15' />
    </div>
    <div>
        <label for="user_password"><?=_('Password:')?> &nbsp;</label>
	<input type='password' name='password' size='15' />
    </div>
    <div>
	<br/>
	<input type="hidden" name="language" id="language" value="" />
	<select id="language-select">
		<option value="es" <?=($language=='es') ? 'selected="selected"' : ''?>data-imagesrc="img/es<?=$_code['es']?>_flag.png">Español</option>
		<option value="pt_BR" <?=($language=='pt_BR') ? 'selected="selected"' : ''?>data-imagesrc="img/br_flag.png">Português</option>
		<option value="en" <?=($language=='en') ? 'selected="selected"' : ''?>data-imagesrc="img/en<?=$_code['en']?>_flag.png">English</option>
	</select>
    </div>
    <div><br/>
        <label>&nbsp;</label>
        <input type="submit" name="access" class='login_button' value="<?=_('Login')?>" />
    </div>
</fieldset>
</form>
<?php

	}

	$error_txt = "";
	if (isset($_POST['access'])) {
		$username = $_POST['username'];
		$password = $_POST['password'];

		if ($username == "") {
			$error_txt .= _("Username is empty")."\n";
		}
		if ($password == "") {
			$error_txt .= _("Password is empty")."\n";
		}
		if ($username && $password) {
			$error_txt .= _("Login Incorrect")."\n";
		}
	}

	if (isset($_POST['access']) && $error_txt != "") {
		print_form(1, $error_txt, substr($language,0,2));
	} else {
		print_form(0, '', substr($language,0,2));
	}

?>
</div>
</body>
</html>
