<?php 

require_once('modules/subscriber.php');
require_once('modules/credit.php');
require_once('modules/configuration.php');
require_once('include/menu.php');
require_once('include/header.php');

print_menu('credits'); ?>

<script type="text/javascript">
	$(function() {

	$("#subscriber_no").autocomplete(
        {
          source: "/rai/ajax.php?service=numbers",
          minLength: 2,
          search: function(event, ui) { $('#subscriber_no').addClass('ac_loading'); },
          response: function(event, ui) {
			$('#subscriber_no').removeClass('ac_loading');
        }
          });
	});
</script>
<br/><br/><br/><br/>

<?php

function check_data() {
	$error_txt = "";
	if ($_SESSION['add_credit']['subscriber_no'] == "") {
		$error_txt .= _("Subscriber number")." "._("is empty")."<br/>";
	}
	$amount = $_SESSION['add_credit']['amount'];
	if ($amount == "" || $amount == 0 || !is_numeric($amount)) {
		$error_txt .= _("Invalid amount")."<br/>";
	}
	if ($error_txt != "") {
		print_form($error_txt);
		print "</div></body></html>";
		exit();
	}
}

function print_form($errors="") {

	$subscriber_no = ($_POST['subscriber_no'] != '') ? $_POST['subscriber_no'] : '';
	$amount = ($_POST['amount'] != '') ? $_POST['amount'] : '';
	$site = new Configuration();
	$info = $site->getSite();
	$internalprefix = $info->postcode.$info->pbxcode;

?>

<div id="stylized" class="myform add_credit_form">
	<form id="form" name="form" method="post" action="credit.php">
	<h1><?= _("Add Credit") ?></h1><br/>
	<span style='color: red; font-size: 14px;'><?= $errors ?></span><br/>
	<label><?= _("Subscriber number") ?>
	<span class="small"><?= _("Enter digits to search for a subscriber.") ?></span>
	</label>
	<input type="text" placeholder="<?=$internalprefix?>XXXXX" name="subscriber_no" id="subscriber_no"
		   value="<?=$_SESSION['add_credit']['subscriber_no']?>"/>

	<label><?= _("Amount") ?>
	<span class="small"><?= _("Amount to add") ?></span>
	</label>
	<input autocomplete="off" placeholder="000" type="text" name="amount" id="amount"
		   value="<?=$_SESSION['add_credit']['amount']?>"/><br/>
	<button type="submit" id="add_credit" name="add_credit" value="1"><?= _("Next") ?> <img src="img/chevron-double-right.svg" /> </button>
	<div class="spacer"></div>
	</form>
</div>

<?
}	// End print_form()

function print_confirm() { ?>
	<div id="stylized" class="confirm">
	<h1><?= _("Add Credit") ?></h1><br/>
	<?= _('Are you sure you want to add credit of') ?>
	<span class="notice"><?=$_SESSION['add_credit']['amount']?></span>
	<?= _('pesos to the account of')?><br />
	<span class="notice_r"><?=$_SESSION['add_credit']['user']?></span><?=_('?')?><br />
	<?= _('This will result in a new balance of')?>
	<span class="notice"><?=($_SESSION['add_credit']['amount'] + $_SESSION['add_credit']['prev_amount'])?></span> pesos.
	<form id="form" name="form" method="post" action="credit.php">
	<button type="submit" name="add_credit" value="-1"><img src="img/x-circle-fill.svg" /> <?= _("Cancel") ?></button>
	<button type="submit" name="add_credit" value="3"><img src="img/chevron-double-left.svg" /> <?= _("Modify") ?></button>
	<button type="submit" name="add_credit" value="2"><?= _("Add") ?> <img src="img/check-circle-fill.svg" /></button>
	</form>
	</div>
<? }

if (!isset($_POST['add_credit'])) {
	print_form();
	print "</div></body></html>";
	exit();
}

if ($_POST['add_credit'] == "-1") {
	$_SESSION['add_credit'] = array();
	print_form();
	print "</div></body></html>";
	exit();
}

if ($_POST['add_credit'] == "3") {
	print_form();
	print "</div></body></html>";
	exit();
}

if ($_POST['add_credit'] == "1") {
	$_SESSION['add_credit']['subscriber_no'] = $_POST['subscriber_no'];
	$_SESSION['add_credit']['amount'] = $_POST['amount'];
	check_data();
	$sub = new Subscriber();
	try {
		$sub->get($_POST['subscriber_no']);
	} catch (SubscriberException $e) {
		print_form($e->getMessage());
		exit("</div></body></html>");
	}
	$_SESSION['add_credit']['user'] = $sub->name;
	$_SESSION['add_credit']['prev_amount'] = $sub->balance;
	print_confirm();
	print "</div></body></html>";
	exit();
}

if ($_POST['add_credit'] != "2") {
	print "</div></body></html>";
	exit();
}

check_data();

echo "<center>";
$cred = new Credit();
try {
	$cred->add($_SESSION['add_credit']['subscriber_no'],$_SESSION['add_credit']['amount']);
	echo "<img src='img/true.png' width='200' height='170' /><br/><br/>";
	echo "<span style='font-size: 20px;'>"._("Credit of")." <b>".$_SESSION['add_credit']['amount']."</b> ";
	echo _("pesos successfully added to subscriber")." <b>".$_SESSION['add_credit']['user']."</b>.</span><br/><br/><br/>";
	echo "<a href='credit.php'><button class='b1'>"._("Go Back")."</button></a>";
	$_SESSION['add_credit'] = array();
} catch (CreditException $e) {
	echo "<img src='img/false.png' width='200' height='170' /><br/><br/>";
	echo "<span style='font-size: 20px; color: red;'>"._("ERROR UPDATING BALANCE!")."<br/>".$e->getMessage()." </span><br/><br/><br/><br/>";
	echo "<a href='credit.php'><button class='b1'>"._("Go Back")."</button></a>";
}
echo "</center>";

?>
		</div>
	</body>

</html>
