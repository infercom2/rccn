<?

require('modules/subscriber.php');
require('modules/configuration.php');
$no_title = 1;
require('include/header.php');

if (!isset($_GET['id']) && !isset($_POST['sip_id'])) {
	exit();
}

function print_form($post_data, $errors, $sub) {
	
?>
	<br/>
	<div id="stylized" class="myform">
		<form id="form" name="form" method="post" action="subscriber_edit.php">
		<h1><?= _("Edit Subscriber") ?></h1><br/>

	<input type="hidden" name="sip_id" value="<?=$_GET['id']?>" />

	<span style='color: red; font-size: 12px;'><?= $errors ?></span><br/>

        <label><?= _("Name") ?>
        <span class="small"><?= _("Subscriber Name") ?></span>
        </label>
        <input type="text" name="firstname" id="firstname" value="<?=$sub->name?>"/>

	<label><?= _("Subscriber number") ?>
	<span class="small"><?= _("Subscriber number") ?></span>
	</label>
	<input type="text" style="background: #f3fff3; color:grey" name="callerid" id="callerid" value="<?=$sub->msisdn?>" readonly/>
	<label><?=_("Equipment")?>
	<span class="small"><?=_("a short description of the phone and model")?>
	</span>
	</label>
	<input type="text" name="equipment" id="equipment" value="<?=$sub->equipment?>" />

<?
try {
	$loc = new Configuration();
	$locations = $loc->getLocations();
} catch (ConfigurationException $e) {
	echo "&nbsp;&nbsp;Error getting locations";
}
if (count($locations) > 1) { ?>

                <label><?= _("Location") ?>
                <span class="small"><?= _("Subscriber location") ?></span>
                </label>
				<select name='location' id='location'>

<? foreach ($locations as $rloc) {
		if ($sub->location == $rloc->name) {
		echo "<option value='".$rloc->name."' selected='selected'>".$rloc->name."</option>";
		} else {
			echo "<option value='".$rloc->name."'>".$rloc->name."</option>";
		}
	}
	echo "</select>";
} ?>

<table class="subscr_fields">
<tbody>
<tr>
  <td>
	<label><?= _("Subscription Paid") ?>
	  <span class="small"><?= _("Check for yes uncheck for no") ?></span>
	</label>
	<? $checked = ($sub->subscription_status == 0) ? '' : 'checked=checked'; ?>
	<input type="checkbox" name="subscription_status" id="subscription_status" value="1" <?=$checked?> />
	</td>
  <td>
	<label><?= _("Authorized") ?>
	  <span class="small"><?= _("Check for yes uncheck for no") ?></span>
	</label>
	<? $checked = ($sub->authorized == 0) ? '' : 'checked=checked'; ?>
	<input type="checkbox" name="authorized" id="authorized" value="1" <?=$checked?>/>
  </td>
</tr>
<tr><td>
	<label><?= _("Roaming") ?>
	<span class="small"><?= _("Check for yes uncheck for no") ?></span>
	</label>
	<? $checked = ($sub->roaming == 0) ? '' : 'checked=checked'; ?>
	<input type="checkbox" name="roaming" id="roaming" value="1" <?=$checked?>/><br/>
</td><td>
	<div style="position:relative; left: -30px; width: max-content;">
        <label><?= _("Credit") ?>
        <span class="small"><?= _("Account Balance") ?></span>
        </label>
        <input type="text" style="background: #f3fff3; color:grey" readonly="yes" name="balance" id="balance" value="<?=$sub->balance?>"/></div>

</td></tr>
</tbody>

</table>

	<button type="submit" name="edit_subscriber"><?= _("Save") ?></button>
	<div class="spacer"></div>
	</form>
</div>
<?
}

$sub = new Subscriber();
$error_txt = "";
try {
	if (isset($_GET['id'])) { // msisdn is passed.
		$sub->get($_GET['id']);
	}
	/*$name = ($_POST['firstname'] != '') ? $_POST['firstname'] : $sub->name;
	$callerid = ($_POST['callerid'] != '') ? $_POST['callerid'] : $sub->msisdn;
	$location = ($_POST['location'] != '') ? $_POST['location'] : $sub->location;
	$equipment = ($_POST['equipment'] != '') ? $_POST['equipment'] : $sub->equipment; */
} catch (SubscriberException $e) {
	echo "<img src='img/false.png' width='200' height='170' /><br/><br/>";
	echo "<span style='font-size: 20px; color: red;'>"._("ERROR GETTING SUBSCRIBER INFO!</br>").
		  $e->getMessage()." </span><br/><br/><br/><br/>";
	echo "<a href='provisioning.php'><button class='b1'>Go Back</button></a>";
	exit();
}

if (!isset($_POST['edit_subscriber'])) {
	print_form(0, '', $sub);
	exit();
}

// form pressed verify if any data is missing
$firstname = (isset($_POST['firstname'])) ? $_POST['firstname'] : '';
$callerid = (isset($_POST['callerid'])) ? $_POST['callerid'] : '';
$authorized = (isset($_POST['authorized'])) ? $_POST['authorized'] : '0';
$location = (isset($_POST['location'])) ? $_POST['location'] : '';
$equipment = (isset($_POST['equipment'])) ? $_POST['equipment']: '';
$roaming = (isset($_POST['roaming'])) ? $_POST['roaming'] : '0';

if ($firstname == '') {
	$error_txt .= _("Name is empty")."<br/>";
}
if ($callerid == '' || strlen($callerid) != 11) {
	$error_txt .= _("Subscriber number is invalid")."<br/>";
}

if ($error_txt != "") {
	print_form(1, $error_txt, $sub);
	exit();
}

echo "<center>";
try {
	#$sub->get($_POST['msisdn']);
	$sub->set("", $callerid, $firstname, "", "", "", "",
			  $location, $equipment, $roaming);

	if ($_POST['authorized'] == 1) {
		$sub->authorized = 1;
	} else {
		$sub->authorized = 0;
	}

	if ($_POST['subscription_status'] == 1) {
		$sub->subscription_status = 1;
	} else {
		$sub->subscription_status = 0;
	}

	$sub->edit();
	echo "<img src='img/true.png' width='200' height='170' /><br/><br/>";
	echo "<span style='font-size: 20px;'>"._("Subscriber number").": <b>$callerid</b> "._("successfully modified")."<br/><br/>";
	echo "<a href='#'  onclick=\"parent.jQuery.fancybox.close()\"><button class='b1'>"._("Close")."</button></a>";
} catch (SubscriberException $e) {
	echo "<img src='img/false.png' width='200' height='170' /><br/><br/>";
	echo "<span style='font-size: 20px; color: red;'>"._("ERROR SAVING SUBSCRIBER!")." ".$e->getMessage()." </span><br/><br/><br/><br/>";
	echo "<a href='#' onclick=\"parent.jQuery.fancybox.close()\"><button class='b1'>"._("Close")."</button></a>";
}

echo "</center>";

?>
	</body>

</html>
