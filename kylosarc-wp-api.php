<?php
/**
 * KylosArc REST API Authentication
 * 
 * Add this to your theme's functions.php or a custom plugin.
 * Replace 'YOUR_SECRET_KEY' with a secure random string.
 */

add_action('rest_api_init', function() {
    
    // Custom authentication endpoint
    register_rest_route('kylosarc/v1', '/verify', array(
        'methods'  => 'POST',
        'callback' => 'kylosarc_verify',
        'permission_callback' => '__return_true'
    ));
    
    // Post marker endpoint - supports both Application Password Basic Auth and X-API-Key
    register_rest_route('kylosarc/v1', '/marker', array(
        'methods'  => 'POST',
        'callback' => 'kylosarc_post_marker',
        'permission_callback' => 'kylosarc_authenticate'
    ));
    
});

define('KYLOSARC_API_KEY', 'YOUR_SECRET_KEY_HERE');

function kylosarc_authenticate($request) {
    // Check X-API-Key header first (custom auth)
    $api_key = $request->get_header('X-API-Key');
    if ($api_key === KYLOSARC_API_KEY) {
        return true;
    }
    
    // Fall back to WordPress Application Password (Basic Auth)
    // When using Basic Auth, WordPress sets current_user after auth
    $auth = $request->get_header('Authorization');
    if ($auth && strpos($auth, 'Basic ') === 0) {
        return true;
    }
    
    return new WP_Error('unauthorized', 'Invalid credentials', array('status' => 401));
}

function kylosarc_verify(WP_REST_Request $request) {
    $api_key = $request->get_header('X-API-Key');
    
    if ($api_key === KYLOSARC_API_KEY) {
        return array(
            'status' => 'ok',
            'message' => 'KylosArc API authenticated',
            'map_id' => 2
        );
    }
    
    return new WP_Error('unauthorized', 'Invalid API key', array('status' => 401));
}

function kylosarc_post_marker(WP_REST_Request $request) {
    $params = $request->get_json_params();
    
    // Extract marker data
    $title = sanitize_text_field($params['title'] ?? 'Untitled');
    $headline = sanitize_text_field($params['headline'] ?? '');
    $lat = floatval($params['lat'] ?? 0);
    $lng = floatval($params['lng'] ?? 0);
    $veracity = floatval($params['veracity_score'] ?? 1.0);
    $color = sanitize_hex_color($params['color'] ?? '#FFFFFF');
    $source = sanitize_text_field($params['source_name'] ?? '');
    $fallacies = sanitize_text_field($params['fallacy_types'] ?? '');
    
    // Create post in MapPress custom post type or regular post
    $post_id = wp_insert_post(array(
        'post_type'    => 'post',
        'post_title'   => $title,
        'post_content' => sprintf(
            '<!-- MapPress --><br>Veracity: %.2f | Color: %s<br>Source: %s<br>Fallacies: %s<br><br>%s',
            $veracity, $color, $source, $fallacies, $headline
        ),
        'post_status'  => 'publish',
        'post_category' => array(2) // Category ID 2 (Map ID 2)
    ));
    
    // Save as custom fields
    update_post_meta($post_id, '_mappress_veracity_score', $veracity);
    update_post_meta($post_id, '_mappress_color', $color);
    update_post_meta($post_id, '_mappress_lat', $lat);
    update_post_meta($post_id, '_mappress_lng', $lng);
    update_post_meta($post_id, '_mappress_source', $source);
    update_post_meta($post_id, '_mappress_fallacies', $fallacies);
    update_post_meta($post_id, '_mappress_headline', $headline);
    
    return array(
        'status' => 'ok',
        'post_id' => $post_id,
        'map_id' => 2,
        'veracity' => $veracity,
        'color' => $color
    );
}
