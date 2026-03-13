# WordPress Anti-Patterns Mapping

This document provides specific modernization patterns for WordPress legacy PHP applications, mapping common WordPress patterns to their Symfony hexagonal architecture equivalents.

## Database Access Patterns

### `$wpdb->query` → Doctrine DBAL

**Legacy Pattern:**
```php
global $wpdb;

$results = $wpdb->get_results("SELECT * FROM {$wpdb->posts} WHERE post_type = 'product'");

$wpdb->query("UPDATE {$wpdb->posts} SET post_status = 'published' WHERE ID = " . intval($post_id));

$wpdb->prepare("SELECT * FROM {$wpdb->postmeta} WHERE post_id = %d AND meta_key = %s", $post_id, $meta_key);
```

**Modern Symfony Pattern:**
```php
// Repository (Driven Port Implementation)
class PostRepository implements PostRepositoryInterface
{
    public function __construct(
        private EntityManagerInterface $em
    ) {}

    public function findByType(string $type): array
    {
        return $this->em->createQueryBuilder()
            ->select('p')
            ->from(Post::class, 'p')
            ->where('p.type = :type')
            ->setParameter('type', $type)
            ->getQuery()
            ->getResult();
    }

    public function updateStatus(int $postId, string $status): void
    {
        $post = $this->em->find(Post::class, $postId);

        if ($post === null) {
            throw new PostNotFoundException($postId);
        }

        $post->setStatus($status);
        $this->em->flush();
    }

    public function findMetaByPostId(int $postId, string $metaKey): ?PostMeta
    {
        return $this->em->createQueryBuilder()
            ->select('m')
            ->from(PostMeta::class, 'm')
            ->where('m.postId = :postId')
            ->andWhere('m.metaKey = :metaKey')
            ->setParameter('postId', $postId)
            ->setParameter('metaKey', $metaKey)
            ->getQuery()
            ->getOneOrNullResult();
    }
}

// Use Case / Application Service
class PostManagementService
{
    public function __construct(
        private PostRepositoryInterface $repository
    ) {}

    public function getProducts(): array
    {
        return $this->repository->findByType('product');
    }

    public function publishPost(int $postId): void
    {
        $this->repository->updateStatus($postId, 'published');
    }
}
```

---

### `$wpdb->prepare` → Doctrine QueryBuilder with Parameterized Queries

**Legacy Pattern:**
```php
global $wpdb;

$sql = $wpdb->prepare(
    "SELECT ID, post_title FROM {$wpdb->posts} WHERE post_author = %d AND post_status = %s",
    $author_id,
    'publish'
);

$wpdb->prepare(
    "INSERT INTO {$wpdb->postmeta} (post_id, meta_key, meta_value) VALUES (%d, %s, %s)",
    $post_id,
    $meta_key,
    $meta_value
);
```

**Modern Symfony Pattern:**
```php
class PostQueryService
{
    public function __construct(
        private EntityManagerInterface $em
    ) {}

    public function findByAuthorAndStatus(int $authorId, string $status): array
    {
        return $this->em->createQueryBuilder()
            ->select('p.id', 'p.title')
            ->from(Post::class, 'p')
            ->where('p.author = :authorId')
            ->andWhere('p.status = :status')
            ->setParameter('authorId', $authorId)
            ->setParameter('status', $status)
            ->getQuery()
            ->getResult();
    }

    public function createMeta(int $postId, string $key, string $value): PostMeta
    {
        $meta = new PostMeta();
        $meta->setPostId($postId);
        $meta->setMetaKey($key);
        $meta->setMetaValue($value);

        $this->em->persist($meta);
        $this->em->flush();

        return $meta;
    }
}
```

---

## Hooks & Event System

### `add_action` / `add_filter` → Symfony EventDispatcher

**Legacy Pattern:**
```php
// Action hooks
add_action('init', 'custom_init_function');
add_action('save_post', 'save_post_callback', 10, 3);
add_action('wp_enqueue_scripts', 'enqueue_assets');
add_action('template_redirect', 'custom_template_redirect');

// Filter hooks
add_filter('the_content', 'modify_content');
add_filter('excerpt_length', 'custom_excerpt_length', 999);
add_filter('wp_nav_menu_items', 'add_menu_items', 10, 2);
```

**Modern Symfony Pattern:**
```php
// Event Definition
class PostInitializedEvent extends Event
{
    public const NAME = 'post.initialized';

    public function __construct(
        private ?int $postId = null
    ) {}

    public function getPostId(): ?int
    {
        return $this->postId;
    }
}

class SavePostEvent extends Event
{
    public const NAME = 'post.save';

    public function __construct(
        private Post $post,
        private bool $isNew
    ) {}

    public function getPost(): Post
    {
        return $this->post;
    }

    public function isNew(): bool
    {
        return $this->isNew;
    }
}

// Event Listener (replaces add_action)
class PostInitializeListener
{
    public function __construct(
        private PostService $postService
    ) {}

    #[AsEventListener(event: PostInitializedEvent::NAME)]
    public function onPostInit(PostInitializedEvent $event): void
    {
        // Initialization logic
    }
}

class SavePostListener
{
    public function __construct(
        private PostRepositoryInterface $repository,
        private EntityManagerInterface $em
    ) {}

    #[AsEventListener(event: SavePostEvent::NAME)]
    public function onSavePost(SavePostEvent $event): void
    {
        $post = $event->getPost();

        if ($event->isNew()) {
            $post->setCreatedAt(new \DateTimeImmutable());
        }

        $post->setUpdatedAt(new \DateTimeImmutable());
        $this->em->flush();
    }
}

// Event Subscriber (replaces add_filter)
class ContentFilterSubscriber implements EventSubscriberInterface
{
    public static function getSubscribedEvents(): array
    {
        return [
            ContentFilterEvent::class => 'onContentFilter'
        ];
    }

    public function onContentFilter(ContentFilterEvent $event): void
    {
        $content = $event->getContent();
        // Modify content
        $event->setContent($modifiedContent);
    }
}

// Dispatching Events (replaces add_action calls)
class PostController extends AbstractController
{
    public function __construct(
        private EventDispatcherInterface $eventDispatcher
    ) {}

    public function save(Request $request, int $id = null): Response
    {
        $post = $id ? $this->repository->find($id) : new Post();
        // ... populate post

        $isNew = $id === null;
        $this->eventDispatcher->dispatch(new SavePostEvent($post, $isNew));

        return $this->redirectToRoute('post_show', ['id' => $post->getId()]);
    }
}
```

---

## Options & Configuration

### `update_option` / `get_option` → Symfony Configuration Service

**Legacy Pattern:**
```php
// Reading options
$site_name = get_option('blogname');
$admin_email = get_option('admin_email');
$theme_options = get_option('my_theme_options');

// Writing options
update_option('blogname', 'New Site Name');
update_option('my_theme_options', $options_array);

// With autoload
update_option('custom_setting', $value, true); // autoload = yes
```

**Modern Symfony Pattern:**
```php
# .env
SITE_NAME=My Site
ADMIN_EMAIL=admin@example.com

# config/packages/settings.yaml
parameters:
    site.name: '%env(SITE_NAME)%'
    site.admin_email: '%env(ADMIN_EMAIL)%'
    theme.options:
        primary_color: '#0073aa'
        layout: 'full-width'

# Settings Service
class SettingsService
{
    public function __construct(
        #[Autowire('%site.name%')]
        private string $siteName,

        #[Autowire('%site.admin_email%')]
        private string $adminEmail,

        #[Autowire('%theme.options%')]
        private array $themeOptions,

        private ParameterBagInterface $params
    ) {}

    public function get(string $key, mixed $default = null): mixed
    {
        return $this->params->get($key, $default);
    }

    public function set(string $key, mixed $value): void
    {
        $this->params->set($key, $value);
    }

    public function getThemeOptions(): array
    {
        return $this->themeOptions;
    }
}

// Domain-specific Settings
class ThemeOptions
{
    public function __construct(
        private SettingsService $settings
    ) {}

    public function getPrimaryColor(): string
    {
        return $this->settings->get('theme.options.primary_color', '#0073aa');
    }

    public function setPrimaryColor(string $color): void
    {
        $options = $this->settings->get('theme.options', []);
        $options['primary_color'] = $color;
        $this->settings->set('theme.options', $options);
    }
}
```

---

## Asset Management

### `wp_enqueue_script` / `wp_enqueue_style` → Webpack Encore

**Legacy Pattern:**
```php
// Enqueue scripts
wp_enqueue_script('jquery');
wp_enqueue_script('my-script', get_template_directory_uri() . '/js/my-script.js', ['jquery'], '1.0.0', true);

// Enqueue styles
wp_enqueue_style('my-style', get_stylesheet_uri());
wp_enqueue_style('custom-css', get_template_directory_uri() . '/css/custom.css', [], '1.0.0');

// Register first, then enqueue
wp_register_script('my-plugin-script', plugins_url('js/plugin.js', __FILE__), ['jquery'], '1.0', true);
wp_enqueue_script('my-plugin-script');

// Localization
wp_enqueue_script('my-script', get_template_directory_uri() . '/js/my-script.js', [], '1.0', true);
wp_localize_script('my-script', 'myScriptVars', [
    'ajaxUrl' => admin_url('admin-ajax.php'),
    'nonce' => wp_create_nonce('my-nonce')
]);
```

**Modern Symfony Pattern:**
```yaml
# webpack.config.js (using Webpack Encore)
const Encore = require('@symfony/webpack-encore');

Encore
    .setOutputPath('public/build/')
    .setPublicPath('/build')
    .addEntry('app', './assets/app.js')
    .addEntry('admin', './assets/admin.js')
    .addStyleEntry('styles', './assets/styles/main.scss')
    .enableSingleRuntimeChunk()
    .enableSassLoader()
    .enablePostCssLoader()
    .splitEntryChunks();

module.exports = Encore.getWebpackConfig();
```

```javascript
// assets/app.js
import $ from 'jquery';
import './styles/main.scss';

// Webpack handles dependencies automatically
import MyComponent from './components/MyComponent';

// Dynamic imports for code splitting
const loadAdmin = () => import(/* webpackChunkName: "admin" */ './admin');
```

```php
// Twig template (replaces wp_enqueue_script)
{# Base layout #}
{% block stylesheets %}
    {{ encore_entry_link_tags('styles') }}
{% endblock %}

{% block javascripts %}
    {{ encore_entry_script_tags('app') }}
{% endblock %}
```

```php
// Controller with AJAX (replaces wp_localize_script)
class AjaxController extends AbstractController
{
    #[Route('/ajax/data', name: 'ajax_data')]
    public function getData(Request $request): JsonResponse
    {
        $this->denyAccessUnlessGranted('IS_AUTHENTICATED_FULLY');

        // Use CSRF token from Symfony form
        $token = $request->headers->get('X-CSRF-Token');

        if (!$this->isCsrfTokenValid('ajax', $token)) {
            return $this->json(['error' => 'Invalid token'], 403);
        }

        return $this->json([
            'data' => $this->dataService->getData(),
            'csrfToken' => $this->csrfTokenManager->refreshToken('ajax')->getValue()
        ]);
    }
}
```

```javascript
// assets/ajax.js (replaces admin-ajax.php calls)
import axios from 'axios';

const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

axios.defaults.headers.common['X-CSRF-Token'] = csrfToken;

export async function fetchData() {
    const response = await axios.get('/ajax/data');
    return response.data;
}
```

---

## Custom Post Types & Taxonomies

### Registering CPTs → Doctrine Entities with Repository

**Legacy Pattern:**
```php
function create_product_post_type() {
    register_post_type('product', [
        'labels' => [
            'name' => __('Products'),
            'singular_name' => __('Product')
        ],
        'public' => true,
        'has_archive' => true,
        'supports' => ['title', 'editor', 'thumbnail'],
        'rewrite' => ['slug' => 'products']
    ]);
}
add_action('init', 'create_product_post_type');
```

**Modern Symfony Pattern:**
```php
// Entity (replaces register_post_type)
#[ORM\Entity]
#[ORM\Table(name: 'products')]
#[ORM\HasLifecycleCallbacks]
class Product
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\Column(type: 'string', length: 255)]
    private string $title;

    #[ORM\Column(type: 'text')]
    private string $content;

    #[ORM\Column(type: 'string', length: 20)]
    private string $status = 'draft';

    #[ORM\Column(type: 'datetime')]
    private ?\DateTimeInterface $createdAt = null;

    #[ORM\Column(type: 'datetime')]
    private ?\DateTimeInterface $updatedAt = null;

    // ... getters and setters
}

// Repository
class ProductRepository extends ServiceEntityRepository implements ProductRepositoryInterface
{
    public function __construct(RegistryInterface $registry)
    {
        parent::__construct($registry, Product::class);
    }

    public function findPublished(): array
    {
        return $this->createQueryBuilder('p')
            ->where('p.status = :status')
            ->setParameter('status', 'publish')
            ->orderBy('p.createdAt', 'DESC')
            ->getQuery()
            ->getResult();
    }
}
```

---

## Shortcodes

### `add_shortcode` → Twig Components / Symfony UX

**Legacy Pattern:**
```php
function product_shortcode($atts, $content = null) {
    $atts = shortcode_atts([
        'id' => 0,
        'format' => 'full'
    ], $atts);

    $product = get_post($atts['id']);

    if (!$product) return '';

    return '<div class="product">' .
           '<h2>' . $product->post_title . '</h2>' .
           '<div class="content">' . $product->post_content . '</div>' .
           '</div>';
}
add_shortcode('product', 'product_shortcode');
```

**Modern Symfony Pattern:**
```php
// Twig Component (replaces shortcode)
#[AsTwigComponent]
class ProductCard
{
    public int $productId;
    public string $format = 'full';

    public function __construct(
        private ProductRepositoryInterface $repository
    ) {}

    public function getProduct(): ?Product
    {
        return $this->repository->find($this->productId);
    }
}
```

```twig
{# templates/components/product_card.html.twig #}
<div class="product">
    <h2>{{ product.title }}</h2>
    {% if format == 'full' %}
        <div class="content">{{ product.content }}</div>
    {% endif %}
</div>
```

```php
// Usage in any template
{{ component('productCard', {productId: 123, format: 'full'}) }}
```

---

## AJAX Handlers

### `wp_ajax_*` / `wp_ajax_nopriv_*` → Symfony Controllers

**Legacy Pattern:**
```php
function my_ajax_handler() {
    check_ajax_referer('my_nonce', 'security');

    $post_id = intval($_POST['post_id']);
    $action = sanitize_text_field($_POST['action_type']);

    // Process request
    $result = process_data($post_id, $action);

    wp_send_json_success(['data' => $result]);
    wp_die();
}
add_action('wp_ajax_my_action', 'my_ajax_handler');
add_action('wp_ajax_nopriv_my_action', 'my_ajax_handler');
```

**Modern Symfony Pattern:**
```php
class AjaxDataController extends AbstractController
{
    public function __construct(
        private DataService $dataService,
        private CsrfTokenManagerInterface $csrfTokenManager
    ) {}

    #[Route('/ajax/process-data', name: 'ajax_process_data', methods: ['POST'])]
    public function processData(Request $request): JsonResponse
    {
        $token = $request->request->get('security');

        if (!$this->csrfTokenManager->isTokenValid(
            new CsrfToken('ajax', $token)
        )) {
            return $this->json(['error' => 'Invalid security token'], 403);
        }

        $postId = $request->request->getInt('post_id');
        $actionType = $request->request->get('action_type');

        try {
            $result = $this->dataService->process($postId, $actionType);
            return $this->json(['success' => true, 'data' => $result]);
        } catch (DataProcessingException $e) {
            return $this->json(['error' => $e->getMessage()], 400);
        }
    }

    #[Route('/ajax/process-data', name: 'ajax_process_data_public', methods: ['POST'])]
    #[IsGranted('ROLE_PUBLIC')]
    public function processDataPublic(Request $request): JsonResponse
    {
        // Same implementation for non-authenticated users
        return $this->processData($request);
    }
}
```

---

## Transients API

### `set_transient` / `get_transient` → Symfony Cache

**Legacy Pattern:**
```php
// Get or set transient
$cache_key = 'my_plugin_data_' . $user_id;
$data = get_transient($cache_key);

if (false === $data) {
    $data = fetchExpensiveData();
    set_transient($cache_key, $data, HOUR_IN_SECONDS);
}

// Delete transient
delete_transient('my_plugin_data');
```

**Modern Symfony Pattern:**
```php
class DataService
{
    public function __construct(
        private CacheInterface $cache
    ) {}

    public function getData(int $userId): array
    {
        $cacheKey = "my_plugin_data_{$userId}";

        return $this->cache->get($cacheKey, function (ItemInterface $item) {
            $item->expiresAfter(\DateInterval::createFromDateString('1 hour'));
            return $this->fetchExpensiveData();
        });
    }

    public function invalidateData(int $userId): void
    {
        $cacheKey = "my_plugin_data_{$userId}";
        $this->cache->delete($cacheKey);
    }
}
```

---

## Summary Table

| WordPress Pattern | Symfony Hexagonal Equivalent |
|-------------------|------------------------------|
| `$wpdb->query` | `EntityManagerInterface` / Repository |
| `$wpdb->prepare` | Doctrine QueryBuilder with parameters |
| `add_action` | `EventDispatcherInterface::dispatch()` |
| `add_filter` | Event Subscriber with `EventSubscriberInterface` |
| `get_option` | `ParameterBagInterface::get()` |
| `update_option` | `ParameterBagInterface::set()` |
| `wp_enqueue_script` | Webpack Encore + `encore_entry_script_tags()` |
| `wp_enqueue_style` | Webpack Encore + `encore_entry_link_tags()` |
| `register_post_type` | Doctrine Entity + Repository |
| `add_shortcode` | Twig Component (`#[AsTwigComponent]`) |
| `wp_ajax_*` | Symfony Controller with `@Route` |
| `set_transient` | `CacheInterface::get()` with callback |

---

## Anti-Patterns to Avoid

1. **Direct `$wpdb` queries in Controllers** — Use repositories
2. **WordPress hooks in Domain entities** — Use Symfony events
3. **Global `get_option` calls throughout** — Inject SettingsService
4. **WordPress AJAX handlers in `functions.php`** — Use Symfony controllers
5. **Shortcodes as functions returning HTML** — Use Twig components
6. **Transients for persistent data** — Use Doctrine for persistence, Cache for performance
7. **Direct `wp_enqueue_*` in services** — Use AssetMapper/Webpack Encore in templates
