<?php
/*
Plugin Name: WordPress AJAX Actions
Plugin URI: https://example.com/
Description: Sample WordPress plugin demonstrating AJAX actions pattern
Version: 1.0.0
Author: WordPress Developer
Author URI: https://example.com/
License: GPL v2 or later
*/

// EXPECT_SIG: PERSISTENCE_SMELL
// EXPECT_SIG: STATE_POLLUTION
// EXPECT_SIG: MODULE_LINK_SMELL
// EXPECT_SIG: MODERN_HYBRID

// Include WordPress bootstrap
// EXPECT_SIG: MODULE_LINK_SMELL
require_once dirname(__FILE__) . '/../../../wp-load.php';

// EXPECT_SIG: STATE_POLLUTION - global $wpdb
global $wpdb;

// Define plugin constants
// EXPECT_SIG: CONSTANT_POLLUTION
define('WPAJAX_VERSION', '1.0.0');
define('WPAJAX_TABLE_NAME', $wpdb->prefix . 'ajax_requests');
define('WPAJAX_NONCE_ACTION', 'wpajax_nonce_action');

// AJAX action handler - register WordPress hooks
// EXPECT_SIG: MODERN_HYBRID - add_action
add_action('wp_ajax_get_user_data', 'wpajax_get_user_data');
add_action('wp_ajax_nopriv_get_user_data', 'wpajax_get_user_data');
add_action('wp_ajax_save_post_meta', 'wpajax_save_post_meta');
add_action('wp_ajax_delete_user_activity', 'wpajax_delete_user_activity');
add_action('wp_ajax_update_settings', 'wpajax_update_settings');

// EXPECT_SIG: MODERN_HYBRID - add_filter
add_filter('wpajax_prepare_user_data', 'wpajax_filter_user_data', 10, 2);

/**
 * Get user data via AJAX
 * Handles the get_user_data AJAX action
 */
function wpajax_get_user_data() {
    // Verify nonce for security
    // EXPECT_SIG: SECURITY_VULN - check_ajax_referer without proper validation
    check_ajax_referer(WPAJAX_NONCE_ACTION, 'security');

    // Get user ID from request
    $user_id = isset($_POST['user_id']) ? (int)$_POST['user_id'] : 0;

    // Validate user ID
    if ($user_id <= 0) {
        // EXPECT_SIG: SECURITY_VULN - wp_send_json_error without sanitized message
        wp_send_json_error('Invalid user ID');
    }

    // EXPECT_SIG: STATE_POLLUTION - global $wpdb
    global $wpdb;

    // Query user data using WordPress database object
    // EXPECT_SIG: PERSISTENCE_SMELL - $wpdb->prepare + $wpdb->get_results
    $query = $wpdb->prepare(
        "SELECT u.ID, u.user_login, u.user_email, u.user_registered, um.meta_value as display_name
         FROM {$wpdb->users} u
         LEFT JOIN {$wpdb->usermeta} um ON u.ID = um.user_id AND um.meta_key = 'display_name'
         WHERE u.ID = %d",
        $user_id
    );

    $user_data = $wpdb->get_results($query);

    if (empty($user_data)) {
        // EXPECT_SIG: STATE_POLLUTION - wp_send_json_error
        wp_send_json_error('User not found');
    }

    // Apply filter to prepared user data
    // EXPECT_SIG: MODERN_HYBRID - apply_filters
    $user_data = apply_filters('wpajax_prepare_user_data', $user_data, $user_id);

    // Return success response
    wp_send_json_success($user_data);
}

/**
 * Filter user data before sending
 *
 * @param array $user_data The user data to filter
 * @param int $user_id The user ID
 * @return array Filtered user data
 */
function wpajax_filter_user_data($user_data, $user_id) {
    // EXPECT_SIG: STATE_POLLUTION - $_POST
    if (isset($_POST['include_meta']) && $_POST['include_meta'] === 'true') {
        // EXPECT_SIG: STATE_POLLUTION - global $wpdb
        global $wpdb;

        // Get user meta
        // EXPECT_SIG: PERSISTENCE_SMELL - $wpdb->prepare
        $meta_query = $wpdb->prepare(
            "SELECT meta_key, meta_value FROM {$wpdb->usermeta} WHERE user_id = %d",
            $user_id
        );

        $user_meta = $wpdb->get_results($meta_query);

        // Add meta to user data
        if (!empty($user_meta)) {
            $user_data[0]->meta = $user_meta;
        }
    }

    return $user_data;
}

/**
 * Save post metadata via AJAX
 * Handles the save_post_meta AJAX action
 */
function wpajax_save_post_meta() {
    // Verify nonce
    check_ajax_referer(WPAJAX_NONCE_ACTION, 'security');

    // EXPECT_SIG: STATE_POLLUTION - $_POST
    $post_id = isset($_POST['post_id']) ? (int)$_POST['post_id'] : 0;
    $meta_key = isset($_POST['meta_key']) ? sanitize_text_field($_POST['meta_key']) : '';
    $meta_value = isset($_POST['meta_value']) ? sanitize_text_field($_POST['meta_value']) : '';

    // Validate inputs
    if ($post_id <= 0 || empty($meta_key)) {
        // EXPECT_SIG: STATE_POLLUTION - wp_send_json_error
        wp_send_json_error('Missing required parameters');
    }

    // Check if post exists
    // EXPECT_SIG: PERSISTENCE_SMELL - $wpdb->get_results
    global $wpdb;
    $post_exists = $wpdb->get_results(
        $wpdb->prepare("SELECT ID FROM {$wpdb->posts} WHERE ID = %d", $post_id)
    );

    if (empty($post_exists)) {
        wp_send_json_error('Post does not exist');
    }

    // Update or add post meta
    // EXPECT_SIG: PERSISTENCE_SMELL - $wpdb->prepare + $wpdb->query
    $result = $wpdb->query(
        $wpdb->prepare(
            "INSERT INTO {$wpdb->postmeta} (post_id, meta_key, meta_value) VALUES (%d, %s, %s)
             ON DUPLICATE KEY UPDATE meta_value = VALUES(meta_value)",
            $post_id,
            $meta_key,
            $meta_value
        )
    );

    if ($result === false) {
        wp_send_json_error('Failed to save metadata');
    }

    // Log activity
    // EXPECT_SIG: STATE_POLLUTION - $_SESSION
    if (!session_id()) {
        session_start();
    }
    // EXPECT_SIG: STATE_POLLUTION - $_SESSION
    $_SESSION['wpajax_last_action'] = 'save_post_meta';
    $_SESSION['wpajax_last_post'] = $post_id;

    wp_send_json_success(array(
        'post_id' => $post_id,
        'meta_key' => $meta_key,
        'message' => 'Metadata saved successfully'
    ));
}

/**
 * Delete user activity via AJAX
 * Handles the delete_user_activity AJAX action
 */
function wpajax_delete_user_activity() {
    // Verify nonce
    check_ajax_referer(WPAJAX_NONCE_ACTION, 'security');

    // EXPECT_SIG: STATE_POLLUTION - $_POST
    $user_id = isset($_POST['user_id']) ? (int)$_POST['user_id'] : 0;
    $activity_id = isset($_POST['activity_id']) ? (int)$_POST['activity_id'] : 0;

    if ($user_id <= 0 || $activity_id <= 0) {
        // EXPECT_SIG: STATE_POLLUTION - wp_send_json_error
        wp_send_json_error('Invalid parameters');
    }

    // EXPECT_SIG: STATE_POLLUTION - global $wpdb
    global $wpdb;

    // Delete activity from custom table
    // EXPECT_SIG: PERSISTENCE_SMELL - $wpdb->prepare + $wpdb->query
    $result = $wpdb->query(
        $wpdb->prepare(
            "DELETE FROM " . WPAJAX_TABLE_NAME . " WHERE id = %d AND user_id = %d",
            $activity_id,
            $user_id
        )
    );

    if ($result === false) {
        wp_send_json_error('Database error occurred');
    }

    // Check if activity was actually deleted
    if ($result === 0) {
        wp_send_json_error('Activity not found or already deleted');
    }

    // Get remaining activities count
    // EXPECT_SIG: PERSISTENCE_SMELL - $wpdb->get_results
    $remaining = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT COUNT(*) as count FROM " . WPAJAX_TABLE_NAME . " WHERE user_id = %d",
            $user_id
        )
    );

    wp_send_json_success(array(
        'deleted' => true,
        'remaining_count' => $remaining[0]->count
    ));
}

/**
 * Update plugin settings via AJAX
 * Handles the update_settings AJAX action
 */
function wpajax_update_settings() {
    // Verify nonce
    check_ajax_referer(WPAJAX_NONCE_ACTION, 'security');

    // Check user capability
    // EXPECT_SIG: STATE_POLLUTION - current_user_can
    if (!current_user_can('manage_options')) {
        wp_send_json_error('Unauthorized');
    }

    // EXPECT_SIG: STATE_POLLUTION - $_POST
    $settings = isset($_POST['settings']) ? $_POST['settings'] : array();

    // Validate settings
    if (!is_array($settings)) {
        wp_send_json_error('Invalid settings format');
    }

    // Update each setting
    // EXPECT_SIG: PERSISTENCE_SMELL - update_option
    foreach ($settings as $key => $value) {
        $option_name = 'wpajax_' . sanitize_key($key);
        update_option($option_name, sanitize_text_field($value));
    }

    // Record update in activity log
    // EXPECT_SIG: STATE_POLLUTION - global $wpdb
    global $wpdb;

    // EXPECT_SIG: PERSISTENCE_SMELL - $wpdb->prepare + $wpdb->insert
    $wpdb->insert(
        WPAJAX_TABLE_NAME,
        array(
            'user_id' => get_current_user_id(),
            'action' => 'settings_updated',
            'data' => json_encode(array_keys($settings)),
            'created_at' => current_time('mysql')
        ),
        array('%d', '%s', '%s', '%s')
    );

    wp_send_json_success('Settings updated successfully');
}

/**
 * Get plugin activity log
 *
 * @param int $limit Number of records to retrieve
 * @return array Activity records
 */
function wpajax_get_activity_log($limit = 50) {
    // EXPECT_SIG: STATE_POLLUTION - global $wpdb
    global $wpdb;

    // EXPECT_SIG: PERSISTENCE_SMELL - $wpdb->prepare + $wpdb->get_results
    $query = $wpdb->prepare(
        "SELECT * FROM " . WPAJAX_TABLE_NAME . " ORDER BY created_at DESC LIMIT %d",
        $limit
    );

    $activities = $wpdb->get_results($query);

    return $activities;
}

/**
 * Clear old activity logs
 *
 * @param int $days_old Delete activities older than this many days
 * @return int Number of records deleted
 */
function wpajax_clear_old_activity($days_old = 30) {
    // EXPECT_SIG: STATE_POLLUTION - global $wpdb
    global $wpdb;

    // EXPECT_SIG: PERSISTENCE_SMELL - $wpdb->prepare + $wpdb->query
    $result = $wpdb->query(
        $wpdb->prepare(
            "DELETE FROM " . WPAJAX_TABLE_NAME . " WHERE created_at < DATE_SUB(NOW(), INTERVAL %d DAY)",
            $days_old
        )
    );

    return $result;
}

/**
 * Initialize plugin database tables
 */
function wpajax_install() {
    // EXPECT_SIG: STATE_POLLUTION - global $wpdb
    global $wpdb;

    $charset_collate = $wpdb->get_charset_collate();

    // SQL for creating custom table
    // EXPECT_SIG: PERSISTENCE_SMELL - $wpdb->query
    $sql = "CREATE TABLE IF NOT EXISTS " . WPAJAX_TABLE_NAME . " (
        id bigint(20) NOT NULL AUTO_INCREMENT,
        user_id bigint(20) NOT NULL,
        action varchar(100) NOT NULL,
        data text,
        created_at datetime NOT NULL,
        PRIMARY KEY  (id),
        KEY user_id (user_id),
        KEY created_at (created_at)
    ) $charset_collate;";

    require_once(ABSPATH . 'wp-admin/includes/upgrade.php');
    dbDelta($sql);
}

// Register activation hook
// EXPECT_SIG: MODERN_HYBRID - register_activation_hook
register_activation_hook(__FILE__, 'wpajax_install');

/**
 * Plugin deactivation cleanup
 */
function wpajax_deactivate() {
    // Clear session data
    // EXPECT_SIG: STATE_POLLUTION - $_SESSION
    if (session_status() === PHP_SESSION_ACTIVE) {
        session_unset();
        session_destroy();
    }
}

// Register deactivation hook
register_deactivation_hook(__FILE__, 'wpajax_deactivate');

// Add admin menu
// EXPECT_SIG: MODERN_HYBRID - add_action
add_action('admin_menu', 'wpajax_add_admin_menu');

function wpajax_add_admin_menu() {
    add_options_page(
        'AJAX Actions Settings',
        'AJAX Actions',
        'manage_options',
        'wpajax-settings',
        'wpajax_settings_page'
    );
}

function wpajax_settings_page() {
    ?>
    <div class="wrap">
        <h1><?php echo esc_html(get_admin_page_title()); ?></h1>
        <form method="post" action="options.php">
            <?php
            // Output security fields
            settings_fields('wpajax_settings_group');

            // Output setting sections and fields
            do_settings_sections('wpajax-settings');

            // Submit button
            submit_button('Save Settings');
            ?>
        </form>

        <h2>Recent Activity</h2>
        <table class="widefat fixed" cellspacing="0">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>
                <?php
                $activities = wpajax_get_activity_log(10);

                foreach ($activities as $activity) {
                    // EXPECT_SIG: PERSISTENCE_SMELL - $wpdb->get_results
                    global $wpdb;
                    $user = $wpdb->get_results(
                        $wpdb->prepare(
                            "SELECT user_login FROM {$wpdb->users} WHERE ID = %d",
                            $activity->user_id
                        )
                    );

                    $username = !empty($user) ? $user[0]->user_login : 'Unknown';
                    ?>
                    <tr>
                        <td><?php echo esc_html($activity->id); ?></td>
                        <td><?php echo esc_html($username); ?></td>
                        <td><?php echo esc_html($activity->action); ?></td>
                        <td><?php echo esc_html($activity->created_at); ?></td>
                    </tr>
                    <?php
                }
                ?>
            </tbody>
        </table>
    </div>
    <?php
}
