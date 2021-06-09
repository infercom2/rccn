<?
require_once('modules/session.php');
$sess = new Session();
$sess->access->logout();
?>
