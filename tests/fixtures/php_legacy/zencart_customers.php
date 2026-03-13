<?php
/*
  $Id: customers.php $
  Zen Cart, Open Source E-Commerce Solutions
  http://www.zen-cart.com

  Copyright (c) 2003 zen-cart developers

  Portions Copyright (c) 2003 osCommerce
  Released under the GNU General Public License
*/

// EXPECT_SIG: PERSISTENCE_SMELL
// EXPECT_SIG: STATE_POLLUTION
// EXPECT_SIG: MODULE_LINK_SMELL

require('includes/application_top.php');

// EXPECT_SIG: STATE_POLLUTION - global $customer_id
global $customer_id;
global $action;

// EXPECT_SIG: MODULE_LINK_SMELL - require order.php class
require DIR_WS_CLASSES . 'order.php';

// EXPECT_SIG: STATE_POLLUTION - $_SESSION
if (isset($_SESSION['customer_id'])) {
  $customer_id = $_SESSION['customer_id'];
}

// Navigation - get action
$LEGACY_ACTION = isset($_GET['action']) ? $_GET['action'] : 'list';

// Initialize order object
$order = new order();

// Handle different actions via switch/case (ZenCart pattern)
switch ($LEGACY_ACTION) {
  case 'new_customer':
    // EXPECT_SIG: PERSISTENCE_SMELL - zen_db_perform
    $sql_data_array = array(
      'customers_firstname' => zen_db_prepare_input($_POST['customers_firstname']),
      'customers_lastname' => zen_db_prepare_input($_POST['customers_lastname']),
      'customers_email_address' => zen_db_prepare_input($_POST['customers_email_address']),
      'customers_telephone' => zen_db_prepare_input($_POST['customers_telephone']),
      'customers_fax' => zen_db_prepare_input($_POST['customers_fax']),
      'customers_newsletter' => (int)$_POST['customers_newsletter'],
      'customers_group_pricing' => (int)$_POST['customers_group_pricing'],
      'customers_password' => zen_encrypt_password($_POST['customers_password']),
      'entry_street_address' => zen_db_prepare_input($_POST['entry_street_address']),
      'entry_city' => zen_db_prepare_input($_POST['entry_city']),
      'entry_country_id' => (int)$_POST['entry_country_id'],
      'entry_state' => zen_db_prepare_input($_POST['entry_state']),
      'entry_postcode' => zen_db_prepare_input($_POST['entry_postcode'])
    );

    zen_db_perform(TABLE_CUSTOMERS, $sql_data_array);
    $customer_id = zen_db_insert_id();

    // Insert address book entry
    // EXPECT_SIG: PERSISTENCE_SMELL - zen_db_perform
    $sql_data_array = array(
      'customers_id' => $customer_id,
      'entry_firstname' => zen_db_prepare_input($_POST['customers_firstname']),
      'entry_lastname' => zen_db_prepare_input($_POST['customers_lastname']),
      'entry_street_address' => zen_db_prepare_input($_POST['entry_street_address']),
      'entry_suburb' => zen_db_prepare_input($_POST['entry_suburb']),
      'entry_postcode' => zen_db_prepare_input($_POST['entry_postcode']),
      'entry_city' => zen_db_prepare_input($_POST['entry_city']),
      'entry_country_id' => (int)$_POST['entry_country_id'],
      'entry_state' => zen_db_prepare_input($_POST['entry_state']),
      'address_date_created' => 'now()'
    );

    zen_db_perform(TABLE_ADDRESS_BOOK, $sql_data_array);
    $address_id = zen_db_insert_id();

    // Update customer record with default address
    // EXPECT_SIG: PERSISTENCE_SMELL - zen_db_perform
    zen_db_perform(TABLE_CUSTOMERS, array('customers_default_address_id' => $address_id), 'update', "customers_id = '" . (int)$customer_id . "'");

    // EXPECT_SIG: STATE_POLLUTION - zen_redirect
    zen_redirect(zen_href_link(FILENAME_CUSTOMERS, 'cID=' . $customer_id));
    break;

  case 'edit_customer':
    // EXPECT_SIG: STATE_POLLUTION - global $customer_id
    global $customer_id;
    $customer_id = (int)$_GET['cID'];

    // Fetch customer data
    // EXPECT_SIG: PERSISTENCE_SMELL - zen_db_perform
    $customer_query = zen_db_query("select * from " . TABLE_CUSTOMERS . " where customers_id = '" . (int)$customer_id . "'");
    $customer = zen_db_fetch_array($customer_query);

    // Fetch address book
    // EXPECT_SIG: PERSISTENCE_SMELL - zen_db_query
    $address_query = zen_db_query("select * from " . TABLE_ADDRESS_BOOK . " where customers_id = '" . (int)$customer_id . "' and address_book_id = '" . (int)$customer['customers_default_address_id'] . "'");
    $address = zen_db_fetch_array($address_query);
    break;

  case 'save_customer':
    $customer_id = (int)$_POST['customers_id'];

    // EXPECT_SIG: PERSISTENCE_SMELL - zen_db_perform for customer update
    $sql_data_array = array(
      'customers_firstname' => zen_db_prepare_input($_POST['customers_firstname']),
      'customers_lastname' => zen_db_prepare_input($_POST['customers_lastname']),
      'customers_email_address' => zen_db_prepare_input($_POST['customers_email_address']),
      'customers_telephone' => zen_db_prepare_input($_POST['customers_telephone']),
      'customers_fax' => zen_db_prepare_input($_POST['customers_fax']),
      'customers_newsletter' => (int)$_POST['customers_newsletter'],
      'customers_group_pricing' => (int)$_POST['customers_group_pricing']
    );

    // Handle password update if provided
    if (!empty($_POST['customers_password'])) {
      $sql_data_array['customers_password'] = zen_encrypt_password($_POST['customers_password']);
    }

    zen_db_perform(TABLE_CUSTOMERS, $sql_data_array, 'update', "customers_id = '" . (int)$customer_id . "'");

    // Update address book
    // EXPECT_SIG: PERSISTENCE_SMELL - zen_db_perform for address update
    $sql_data_array = array(
      'entry_firstname' => zen_db_prepare_input($_POST['entry_firstname']),
      'entry_lastname' => zen_db_prepare_input($_POST['entry_lastname']),
      'entry_street_address' => zen_db_prepare_input($_POST['entry_street_address']),
      'entry_suburb' => zen_db_prepare_input($_POST['entry_suburb']),
      'entry_postcode' => zen_db_prepare_input($_POST['entry_postcode']),
      'entry_city' => zen_db_prepare_input($_POST['entry_city']),
      'entry_country_id' => (int)$_POST['entry_country_id'],
      'entry_state' => zen_db_prepare_input($_POST['entry_state'])
    );

    zen_db_perform(TABLE_ADDRESS_BOOK, $sql_data_array, 'update', "customers_id = '" . (int)$customer_id . "' and address_book_id = '" . (int)$_POST['default_address_id'] . "'");

    // EXPECT_SIG: STATE_POLLUTION - zen_redirect
    zen_redirect(zen_href_link(FILENAME_CUSTOMERS, 'cID=' . $customer_id));
    break;

  case 'delete_customer':
    $customer_id = (int)$_GET['cID'];

    // Check for orders
    // EXPECT_SIG: PERSISTENCE_SMELL - zen_db_query
    $orders_check = zen_db_query("select count(*) as total from " . TABLE_ORDERS . " where customers_id = '" . (int)$customer_id . "'");
    $orders = zen_db_fetch_array($orders_check);

    if ($orders['total'] > 0) {
      // EXPECT_SIG: STATE_POLLUTION - $_SESSION
      $_SESSION['customer_delete_error'] = ERROR_CUSTOMER_HAS_ORDERS;
      // EXPECT_SIG: STATE_POLLUTION - zen_redirect
      zen_redirect(zen_href_link(FILENAME_CUSTOMERS, 'cID=' . $customer_id));
    }

    // Check for addresses
    // EXPECT_SIG: PERSISTENCE_SMELL - zen_db_query
    $addresses_check = zen_db_query("select count(*) as total from " . TABLE_ADDRESS_BOOK . " where customers_id = '" . (int)$customer_id . "'");
    $addresses = zen_db_fetch_array($addresses_check);

    if ($addresses['total'] > 0) {
      // EXPECT_SIG: PERSISTENCE_SMELL - zen_db_query
      zen_db_query("delete from " . TABLE_ADDRESS_BOOK . " where customers_id = '" . (int)$customer_id . "'");
    }

    // Delete customer
    // EXPECT_SIG: PERSISTENCE_SMELL - zen_db_query
    zen_db_query("delete from " . TABLE_CUSTOMERS . " where customers_id = '" . (int)$customer_id . "'");

    // EXPECT_SIG: STATE_POLLUTION - zen_redirect
    zen_redirect(zen_href_link(FILENAME_CUSTOMERS));
    break;

  case 'delete_address':
    $customer_id = (int)$_GET['cID'];
    $address_id = (int)$_GET['address_id'];

    // Don't delete default address
    // EXPECT_SIG: PERSISTENCE_SMELL - zen_db_query
    $check_query = zen_db_query("select customers_default_address_id from " . TABLE_CUSTOMERS . " where customers_id = '" . (int)$customer_id . "'");
    $check = zen_db_fetch_array($check_query);

    if ($check['customers_default_address_id'] == $address_id) {
      // EXPECT_SIG: STATE_POLLUTION - $_SESSION
      $_SESSION['delete_address_error'] = ERROR_ADDRESS_DEFAULT;
      // EXPECT_SIG: STATE_POLLUTION - zen_redirect
      zen_redirect(zen_href_link(FILENAME_CUSTOMERS, 'cID=' . $customer_id));
    }

    // Delete address
    // EXPECT_SIG: PERSISTENCE_SMELL - zen_db_query
    zen_db_query("delete from " . TABLE_ADDRESS_BOOK . " where customers_id = '" . (int)$customer_id . "' and address_book_id = '" . (int)$address_id . "'");

    // EXPECT_SIG: STATE_POLLUTION - zen_redirect
    zen_redirect(zen_href_link(FILENAME_CUSTOMERS, 'cID=' . $customer_id));
    break;

  case 'list':
  default:
    // Default customer listing action
    // EXPECT_SIG: PERSISTENCE_SMELL - zen_db_query for main listing
    $customers_query = "select c.customers_id, c.customers_lastname, c.customers_firstname, c.customers_email_address, c.customers_group_pricing, c.customers_newsletter, a.entry_company, a.entry_city from " . TABLE_CUSTOMERS . " c left join " . TABLE_ADDRESS_BOOK . " a on c.customers_id = a.customers_id and c.customers_default_address_id = a.address_book_id order by c.customers_lastname, c.customers_firstname";

    $customers_split = new splitPageResults($_GET['page'], MAX_DISPLAY_SEARCH_RESULTS, $customers_query, $customers_query_numrows);
    $customers = zen_db_query($customers_query);

    // EXPECT_SIG: STATE_POLLUTION - $_SESSION
    $_SESSION['last_customer_action'] = 'list';
    break;
}

// Build customer dropdown for orders
// EXPECT_SIG: PERSISTENCE_SMELL - zen_db_query
function zen_get_customer_dropdown() {
  $customers_array = array();
  $customers_query = zen_db_query("select customers_id, customers_lastname, customers_firstname from " . TABLE_CUSTOMERS . " order by customers_lastname, customers_firstname");

  while ($customers = zen_db_fetch_array($customers_query)) {
    $customers_array[] = array(
      'id' => $customers['customers_id'],
      'text' => $customers['customers_lastname'] . ', ' . $customers['customers_firstname']
    );
  }

  return $customers_array;
}

// Get customer details
// EXPECT_SIG: PERSISTENCE_SMELL - zen_db_query
function zen_get_customer($customer_id) {
  $customer_query = zen_db_query("select * from " . TABLE_CUSTOMERS . " where customers_id = '" . (int)$customer_id . "'");
  return zen_db_fetch_array($customer_query);
}

// Get customer address book
// EXPECT_SIG: PERSISTENCE_SMELL - zen_db_query
function zen_get_address_book($customer_id) {
  $addresses_query = zen_db_query("select * from " . TABLE_ADDRESS_BOOK . " where customers_id = '" . (int)$customer_id . "' order by address_book_id");
  $addresses = array();

  while ($address = zen_db_fetch_array($addresses_query)) {
    $addresses[] = $address;
  }

  return $addresses;
}

// Get customer order total
// EXPECT_SIG: PERSISTENCE_SMELL - zen_db_query
function zen_get_customers_total($customer_id) {
  $total_query = zen_db_query("select sum(orders_total) as total from " . TABLE_ORDERS . " where customers_id = '" . (int)$customer_id . "' and orders_status in ('" . implode("', '", array_keys(zen_get_order_statuses())) . "')");
  $total = zen_db_fetch_array($total_query);

  return $total['total'];
}

// Initialize message stack
// EXPECT_SIG: STATE_POLLUTION - global $messageStack
global $messageStack;
?>
<!DOCTYPE html>
<html <?php echo HTML_PARAMS; ?>>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=<?php echo CHARSET; ?>">
  <title><?php echo TITLE; ?></title>
  <link rel="stylesheet" type="text/css" href="includes/stylesheet.css">
  <?php
  // EXPECT_SIG: MODULE_LINK_SMELL
  if (file_exists(DIR_WS_INCLUDES . 'javascript.php')) {
    require(DIR_WS_INCLUDES . 'javascript.php');
  }
  ?>
  <script type="text/javascript" src="includes/javascript/customers.js"></script>
</head>
<body marginwidth="0" marginheight="0">
  <div id="pageHeader">
    <table border="0" width="100%" cellspacing="0" cellpadding="0">
      <tr>
        <td><?php echo '<a href="' . zen_href_link(FILENAME_CUSTOMERS) . '">' . zen_image(DIR_WS_IMAGES . 'customers.gif', HEADING_TITLE_CUSTOMERS) . '</a>'; ?></td>
        <td align="right"><?php echo '<a href="' . zen_href_link(FILENAME_CUSTOMERS, 'action=new_customer') . '">' . zen_image(DIR_WS_IMAGES . 'button_new_customer.gif', IMAGE_NEW_CUSTOMER) . '</a>'; ?></td>
      </tr>
    </table>
  </div>
  <table border="0" width="100%" cellspacing="0" cellpadding="2">
    <tr>
      <td><table border="0" width="100%" cellspacing="0" cellpadding="0">
        <tr>
          <td valign="top">
            <table border="0" width="100%" cellspacing="0" cellpadding="2">
              <tr class="dataTableHeadingRow">
                <td class="dataTableHeadingContent"><?php echo TABLE_HEADING_LASTNAME; ?></td>
                <td class="dataTableHeadingContent"><?php echo TABLE_HEADING_FIRSTNAME; ?></td>
                <td class="dataTableHeadingContent"><?php echo TABLE_HEADING_EMAIL; ?></td>
                <td class="dataTableHeadingContent" align="center"><?php echo TABLE_HEADING_ACTION; ?></td>
              </tr>
              <?php
              // Display customers
              if ($customers_split->number_of_rows > 0) {
                while ($customer = zen_db_fetch_array($customers)) {
                  echo '<tr class="dataTableRow" onmouseover="this.style.cursor=\'pointer\'" onClick="document.location.href=\'' . zen_href_link(FILENAME_CUSTOMERS, 'cID=' . $customer['customers_id'] . '&action=edit_customer') . '\'">';
                  echo '<td class="dataTableContent">' . $customer['customers_lastname'] . '</td>';
                  echo '<td class="dataTableContent">' . $customer['customers_firstname'] . '</td>';
                  echo '<td class="dataTableContent">' . $customer['customers_email_address'] . '</td>';
                  echo '<td class="dataTableContent" align="right"><a href="#" onClick="return confirm(\'' . TEXT_DELETE_CUSTOMER_CONFIRM . '\')">' . zen_image(DIR_WS_IMAGES . 'icon_delete.gif', TEXT_DELETE) . '</a>&nbsp;<a href="' . zen_href_link(FILENAME_CUSTOMERS, 'cID=' . $customer['customers_id'] . '&action=edit_customer') . '">' . zen_image(DIR_WS_IMAGES . 'icon_edit.gif', TEXT_EDIT) . '</a></td>';
                  echo '</tr>';
                }
              }
              ?>
              <tr>
                <td colspan="4">
                  <table border="0" width="100%" cellspacing="0" cellpadding="2">
                    <tr>
                      <td class="smallText" valign="top"><?php echo $customers_split->display_count($customers_query_numrows, MAX_DISPLAY_SEARCH_RESULTS, $_GET['page'], TEXT_DISPLAY_NUMBER_OF_CUSTOMERS); ?></td>
                      <td class="smallText" align="right"><?php echo $customers_split->display_links($customers_query_numrows, MAX_DISPLAY_SEARCH_RESULTS, MAX_DISPLAY_PAGE_LINKS, $_GET['page'], zen_get_all_get_params(array('page', 'action'))); ?></td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table></td>
    </tr>
  </table>
</body>
</html>
<?php
require('includes/application_bottom.php');
?>
