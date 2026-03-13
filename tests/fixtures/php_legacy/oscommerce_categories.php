<?php
/*
  $Id: categories.php $
  osCommerce, Open Source E-Commerce Solutions
  http://www.oscommerce.com

  Copyright (c) 2022 osCommerce

  Released under the GNU General Public License
*/

// EXPECT_SIG: PERSISTENCE_SMELL
// EXPECT_SIG: STATE_POLLUTION
// EXPECT_SIG: MODULE_LINK_SMELL

  require('includes/application_top.php');

  // EXPECT_SIG: STATE_POLLUTION - global $languages_id
  global $languages_id;
  global $action;

  // EXPECT_SIG: MODULE_LINK_SMELL
  require(DIR_WS_CLASSES . 'category.php');
  require(DIR_WS_FUNCTIONS . 'categories.php');

  // EXPECT_SIG: STATE_POLLUTION - $_SESSION
  if (isset($_SESSION['category_tree'])) {
    $cat_tree =& $_SESSION['category_tree'];
  }

  $LEGACY_ACTION = isset($_GET['action']) ? $_GET['action'] : 'list';

  // Initialize category object
  $category = new category();

  // Navigation pane change
  if (isset($_GET['cPath'])) {
    $cPath = $_GET['cPath'];
  } else {
    $cPath = '';
  }

  // Handle different actions via switch/case (osCommerce 2.3 pattern)
  switch ($LEGACY_ACTION) {
    case 'new_category':
      // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query
      $categories_query = tep_db_query("select c.categories_id, cd.categories_name, c.categories_image, c.parent_id, c.sort_order, c.date_added, c.last_modified from " . TABLE_CATEGORIES . " c, " . TABLE_CATEGORIES_DESCRIPTION . " cd where c.categories_id = cd.categories_id and cd.language_id = '" . (int)$languages_id . "' order by c.sort_order, cd.categories_name");
      break;

    case 'edit_category':
      // EXPECT_SIG: STATE_POLLUTION - global variable
      global $ languages_id;
      $category_id = (int)$_GET['cID'];

      $category_query = tep_db_query("select * from " . TABLE_CATEGORIES . " where categories_id = '" . (int)$category_id . "'");
      $category_data = tep_db_fetch_array($category_query);

      // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query
      $description_query = tep_db_query("select * from " . TABLE_CATEGORIES_DESCRIPTION . " where categories_id = '" . (int)$category_id . "' and language_id = '" . (int)$languages_id . "'");
      $description_data = tep_db_fetch_array($description_query);
      break;

    case 'save_category':
      $category_id = (int)$_POST['categories_id'];
      $parent_id = (int)$_POST['parent_id'];
      $sort_order = (int)$_POST['sort_order'];
      $categories_name = tep_db_prepare_input($_POST['categories_name']);
      $categories_image = '';

      // Handle image upload
      if (isset($_FILES['categories_image']) && $_FILES['categories_image']['size'] > 0) {
        $categories_image = new upload('categories_image', DIR_WS_IMAGES . 'categories/');
        $categories_image = $categories_image->filename;
      }

      // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query for insert
      $sql_data_array = array(
        'parent_id' => $parent_id,
        'sort_order' => $sort_order,
        'categories_image' => $categories_image,
        'last_modified' => 'now()'
      );

      if ($category_id > 0) {
        tep_db_perform(TABLE_CATEGORIES, $sql_data_array, 'update', "categories_id = '" . (int)$category_id . "'");
        // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query for description update
        tep_db_query("update " . TABLE_CATEGORIES_DESCRIPTION . " set categories_name = '" . tep_db_input($categories_name) . "' where categories_id = '" . (int)$category_id . "' and language_id = '" . (int)$languages_id . "'");
      } else {
        // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query for insert
        tep_db_perform(TABLE_CATEGORIES, $sql_data_array);
        $category_id = tep_db_insert_id();
        // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query for description insert
        tep_db_query("insert into " . TABLE_CATEGORIES_DESCRIPTION . " (categories_id, language_id, categories_name) values ('" . (int)$category_id . "', '" . (int)$languages_id . "', '" . tep_db_input($categories_name) . "')");
      }

      // EXPECT_SIG: STATE_POLLUTION - tep_redirect
      tep_redirect(tep_href_link(FILENAME_CATEGORIES, 'cPath=' . $_POST['cPath']));
      break;

    case 'delete_category':
      // EXPECT_SIG: STATE_POLLUTION - $_SESSION
      if (isset($_SESSION['category_delete_error'])) {
        $messageStack->add_session(ERROR_CATEGORY_HAS_PRODUCTS, 'error');
        unset($_SESSION['category_delete_error']);
      }

      $category_id = (int)$_GET['cID'];

      // Check for products in category
      // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query
      $products_check = tep_db_query("select count(*) as total from " . TABLE_PRODUCTS_TO_CATEGORIES . " where categories_id = '" . (int)$category_id . "'");
      $products = tep_db_fetch_array($products_check);

      if ($products['total'] > 0) {
        // EXPECT_SIG: STATE_POLLUTION - $_SESSION
        $_SESSION['category_delete_error'] = true;
        // EXPECT_SIG: STATE_POLLUTION - tep_redirect
        tep_redirect(tep_href_link(FILENAME_CATEGORIES, 'cPath=' . $cPath . '&cID=' . $category_id));
      }

      // Check for subcategories
      // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query
      $categories_check = tep_db_query("select count(*) as total from " . TABLE_CATEGORIES . " where parent_id = '" . (int)$category_id . "'");
      $categories = tep_db_fetch_array($categories_check);

      if ($categories['total'] > 0) {
        // EXPECT_SIG: STATE_POLLUTION - $_SESSION
        $_SESSION['category_delete_error'] = true;
        // EXPECT_SIG: STATE_POLLUTION - tep_redirect
        tep_redirect(tep_href_link(FILENAME_CATEGORIES, 'cPath=' . $cPath . '&cID=' . $category_id));
      }

      // Delete category
      // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query
      tep_db_query("delete from " . TABLE_CATEGORIES . " where categories_id = '" . (int)$category_id . "'");
      // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query
      tep_db_query("delete from " . TABLE_CATEGORIES_DESCRIPTION . " where categories_id = '" . (int)$category_id . "'");

      // EXPECT_SIG: STATE_POLLUTION - tep_redirect
      tep_redirect(tep_href_link(FILENAME_CATEGORIES, 'cPath=' . $cPath));
      break;

    case 'move_category':
      $category_id = (int)$_GET['cID'];
      $new_parent_id = (int)$_POST['move_to_category_id'];

      // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query
      tep_db_query("update " . TABLE_CATEGORIES . " set parent_id = '" . (int)$new_parent_id . "', last_modified = now() where categories_id = '" . (int)$category_id . "'");

      // EXPECT_SIG: STATE_POLLUTION - tep_redirect
      tep_redirect(tep_href_link(FILENAME_CATEGORIES, 'cPath=' . $cPath));
      break;

    case 'setflag':
      $category_id = (int)$_GET['cID'];
      $flag = (int)$_GET['flag'];

      // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query
      tep_db_query("update " . TABLE_CATEGORIES . " set categories_status = '" . (int)$flag . "', last_modified = now() where categories_id = '" . (int)$category_id . "'");

      // EXPECT_SIG: STATE_POLLUTION - tep_redirect
      tep_redirect(tep_href_link(FILENAME_CATEGORIES, 'cPath=' . $cPath));
      break;

    case 'list':
    default:
      // Default category listing action
      // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query for main listing
      $categories_query = tep_db_query("select c.categories_id, cd.categories_name, c.categories_image, c.parent_id, c.sort_order, c.date_added, c.last_modified, c.categories_status from " . TABLE_CATEGORIES . " c, " . TABLE_CATEGORIES_DESCRIPTION . " cd where c.categories_id = cd.categories_id and cd.language_id = '" . (int)$languages_id . "' and c.parent_id = '0' order by c.sort_order, cd.categories_name");

      // EXPECT_SIG: STATE_POLLUTION - $_SESSION
      $_SESSION['last_category_action'] = 'list';
      break;
  }

  // Build category tree for display
  // EXPECT_SIG: STATE_POLLUTION - global
  global $cPath_array;

  function build_category_tree($parent_id = 0, $level = 0) {
    // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query
    $categories_query = tep_db_query("select c.categories_id, cd.categories_name from " . TABLE_CATEGORIES . " c, " . TABLE_CATEGORIES_DESCRIPTION . " cd where c.categories_id = cd.categories_id and cd.language_id = '" . (int)$languages_id . "' and c.parent_id = '" . (int)$parent_id . "' order by c.sort_order, cd.categories_name");

    $tree = array();
    while ($categories = tep_db_fetch_array($categories_query)) {
      $tree[] = array(
        'id' => $categories['categories_id'],
        'name' => $categories['categories_name'],
        'level' => $level
      );

      // Recursive call for subcategories
      $subtree = build_category_tree($categories['categories_id'], $level + 1);
      $tree = array_merge($tree, $subtree);
    }

    return $tree;
  }

  // Get category path
  function get_category_path($category_id) {
    $cPath = '';

    // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query
    $category_query = tep_db_query("select parent_id from " . TABLE_CATEGORIES . " where categories_id = '" . (int)$category_id . "'");
    $category = tep_db_fetch_array($category_query);

    if ($category['parent_id'] > 0) {
      $cPath = get_category_path($category['parent_id']) . '_';
    }

    return $cPath . $category_id;
  }

  // Initialize breadcrumb
  $breadcrumb = new breadcrumb();
  $breadcrumb->add(NAVBAR_TITLE, tep_href_link(FILENAME_CATEGORIES));
?>
<!DOCTYPE html>
<html <?php echo HTML_PARAMS; ?>>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=<?php echo CHARSET; ?>">
  <title><?php echo TITLE; ?></title>
  <link rel="stylesheet" type="text/css" href="includes/stylesheet.css">
  <?php
  // EXPECT_SIG: MODULE_LINK_SMELL
  if (tep_not_null(HOOK_ADMIN_CATEGORIES)) {
    require(DIR_WS_INCLUDES . 'javascript.php');
  }
  ?>
  <script type="text/javascript" src="includes/javascript/categories.js"></script>
</head>
<body marginwidth="0" marginheight="0">
  <div id="pageHeader">
    <table border="0" width="100%" cellspacing="0" cellpadding="0">
      <tr>
        <td><?php echo '<a href="' . tep_href_link(FILENAME_CATEGORIES) . '">' . tep_image(DIR_WS_IMAGES . 'categories.gif', HEADING_TITLE_CATEGORIES) . '</a>'; ?></td>
        <td align="right"><?php echo '<a href="' . tep_href_link(FILENAME_CATEGORIES, 'action=new_category') . '">' . tep_image(DIR_WS_IMAGES . 'button_new_category.gif', IMAGE_NEW_CATEGORY) . '</a>'; ?></td>
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
                <td class="dataTableHeadingContent"><?php echo TABLE_HEADING_CATEGORIES; ?></td>
                <td class="dataTableHeadingContent" align="center"><?php echo TABLE_HEADING_STATUS; ?></td>
                <td class="dataTableHeadingContent" align="right"><?php echo TABLE_HEADING_ACTION; ?></td>
              </tr>
              <?php
              // Display categories
              $categories = build_category_tree();
              foreach ($categories as $cat) {
                // EXPECT_SIG: PERSISTENCE_SMELL - tep_db_query for status
                $status_query = tep_db_query("select categories_status from " . TABLE_CATEGORIES . " where categories_id = '" . (int)$cat['id'] . "'");
                $status = tep_db_fetch_array($status_query);

                echo '<tr class="dataTableRow" onmouseover="this.style.cursor=\'pointer\'" onClick="document.location.href=\'' . tep_href_link(FILENAME_CATEGORIES, 'cPath=' . get_category_path($cat['id']) . '&cID=' . $cat['id']) . '\'">';
                echo '<td class="dataTableContent">';
                if ($cat['level'] > 0) {
                  echo str_repeat('&nbsp;&nbsp;', $cat['level']) . '&nbsp;&nbsp;';
                }
                echo $cat['name'];
                echo '</td>';
                echo '<td class="dataTableContent" align="center">';
                if ($status['categories_status'] == '1') {
                  echo tep_image(DIR_WS_IMAGES . 'icon_status_green.gif', IMAGE_ICON_STATUS_GREEN, 10, 10) . '&nbsp;<a href="' . tep_href_link(FILENAME_CATEGORIES, 'action=setflag&flag=0&cID=' . $cat['id']) . '">' . tep_image(DIR_WS_IMAGES . 'icon_status_red_light.gif', IMAGE_ICON_STATUS_RED_LIGHT, 10, 10) . '</a>';
                } else {
                  echo '<a href="' . tep_href_link(FILENAME_CATEGORIES, 'action=setflag&flag=1&cID=' . $cat['id']) . '">' . tep_image(DIR_WS_IMAGES . 'icon_status_green_light.gif', IMAGE_ICON_STATUS_GREEN_LIGHT, 10, 10) . '</a>&nbsp;' . tep_image(DIR_WS_IMAGES . 'icon_status_red.gif', IMAGE_ICON_STATUS_RED, 10, 10);
                }
                echo '</td>';
                echo '<td class="dataTableContent" align="right"><a href="#" onClick="return confirm(\'' . TEXT_DELETE_CATEGORY_CONFIRM . '\')">' . tep_image(DIR_WS_IMAGES . 'icon_delete.gif', TEXT_DELETE) . '</a>&nbsp;<a href="#" onClick="return confirm(\'' . TEXT_MOVE_CATEGORY_CONFIRM . '\')">' . tep_image(DIR_WS_IMAGES . 'icon_move.gif', TEXT_MOVE) . '</a>&nbsp;<a href="' . tep_href_link(FILENAME_CATEGORIES, 'cPath=' . $cPath . '&cID=' . $cat['id'] . '&action=edit_category') . '">' . tep_image(DIR_WS_IMAGES . 'icon_edit.gif', TEXT_EDIT) . '</a></td>';
                echo '</tr>';
              }
              ?>
              <tr>
                <td colspan="3">
                  <table border="0" width="100%" cellspacing="0" cellpadding="2">
                    <tr>
                      <td valign="top"><?php echo TEXT_CATEGORIES; ?></td>
                      <td align="right" valign="top"><?php echo '<a href="' . tep_href_link(FILENAME_CATEGORIES, 'action=new_category') . '">' . tep_image(DIR_WS_IMAGES . 'button_new_category.gif', IMAGE_NEW_CATEGORY) . '</a>'; ?></td>
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
  require(DIR_WS_INCLUDES . 'application_bottom.php');
?>