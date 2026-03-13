# Generic PHP Anti-Patterns Mapping

This document provides specific modernization patterns for generic legacy PHP applications (non-framework-specific), mapping common PHP patterns to their Symfony hexagonal architecture equivalents.

## Database Access Patterns

### `mysql_query()` / `mysqli_query()` → Doctrine DBAL

**Legacy Pattern:**
```php
// Direct mysql_* functions (deprecated)
$result = mysql_query("SELECT * FROM users WHERE id = $userId");
$row = mysql_fetch_assoc($result);

// mysqli procedural
$conn = mysqli_connect("localhost", "root", "", "mydb");
$result = mysqli_query($conn, "SELECT * FROM users");
while ($row = mysqli_fetch_assoc($result)) {
    echo $row['name'];
}

// mysqli with prepared statements
$stmt = mysqli_prepare($conn, "SELECT * FROM users WHERE id = ?");
mysqli_stmt_bind_param($stmt, "i", $userId);
mysqli_stmt_execute($stmt);
$result = mysqli_stmt_get_result($stmt);

// Raw SQL with string concatenation (SQL injection vulnerable)
$sql = "SELECT * FROM users WHERE name = '" . $_POST['name'] . "'";
$result = mysqli_query($conn, $sql);

// Multiple queries ( UNION, subqueries )
$sql = "SELECT * FROM products UNION SELECT * FROM archived_products";
$result = mysqli_query($conn, $sql);

// Transactions with manual rollback
mysqli_autocommit($conn, false);
mysqli_query($conn, "INSERT INTO orders...");
mysqli_query($conn, "INSERT INTO order_items...");
if ($error) {
    mysqli_rollback($conn);
} else {
    mysqli_commit($conn);
}
```

**Modern Symfony Pattern:**
```php
// Entity
#[ORM\Entity]
#[ORM\Table(name: 'users')]
class User
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\Column(type: 'string', length: 255)]
    private string $name;

    #[ORM\Column(type: 'string', length: 255, unique: true)]
    private string $email;

    #[ORM\Column(type: 'datetime')]
    private ?DateTimeInterface $createdAt = null;

    // Getters and setters...
}

// Repository Interface (Driven Port)
interface UserRepositoryInterface
{
    public function find(int $id): ?User;
    public function findByEmail(string $email): ?User;
    public function findAll(): array;
    public function save(User $user): void;
    public function remove(User $user): void;
}

// Repository Implementation (Driven Adapter)
class UserRepository extends ServiceEntityRepository implements UserRepositoryInterface
{
    public function __construct(RegistryInterface $registry)
    {
        parent::__construct($registry, User::class);
    }

    public function find(int $id): ?User
    {
        return $this->findOneBy(['id' => $id]);
    }

    public function findByEmail(string $email): ?User
    {
        return $this->findOneBy(['email' => $email]);
    }

    public function findAll(): array
    {
        return $this->findAll();
    }

    public function save(User $user): void
    {
        $this->getEntityManager()->persist($user);
        $this->getEntityManager()->flush();
    }

    public function remove(User $user): void
    {
        $this->getEntityManager()->remove($user);
        $this->getEntityManager()->flush();
    }
}

// Application Service with QueryBuilder (for complex queries)
class UserService
{
    public function __construct(
        private UserRepositoryInterface $userRepository,
        private EntityManagerInterface $entityManager
    ) {}

    public function getUser(int $id): ?UserDTO
    {
        $user = $this->userRepository->find($id);
        return $user ? UserDTO::fromEntity($user) : null;
    }

    public function searchByName(string $name): array
    {
        return array_map(
            fn(User $u) => UserDTO::fromEntity($u),
            $this->userRepository->findBy(['name' => $name])
        );
    }

    // Complex query with JOINs using QueryBuilder
    public function getUsersWithOrders(): array
    {
        return $this->entityManager->createQueryBuilder()
            ->select('u', 'o')
            ->from(User::class, 'u')
            ->leftJoin('u.orders', 'o')
            ->getQuery()
            ->getResult();
    }

    // Native SQL for legacy data migrations
    public function fetchLegacyData(): array
    {
        $conn = $this->entityManager->getConnection();
        $sql = "SELECT * FROM legacy_users WHERE status = 'active'";
        $stmt = $conn->prepare($sql);
        $stmt->executeQuery();

        return $stmt->fetchAllAssociative();
    }

    // Transaction support
    public function createUserWithDefaultOrder(CreateUserDTO $dto): User
    {
        return $this->entityManager->transactional(function (EntityManagerInterface $em) use ($dto) {
            $user = new User();
            $user->setName($dto->name);
            $user->setEmail($dto->email);

            $em->persist($user);
            $em->flush();

            // Create default order
            $order = new Order();
            $order->setUser($user);
            $order->setStatus('pending');

            $em->persist($order);
            $em->flush();

            return $user;
        });
    }
}

// DTO for data transfer
class UserDTO
{
    public function __construct(
        public readonly int $id,
        public readonly string $name,
        public readonly string $email
    ) {}

    public static function fromEntity(User $user): self
    {
        return new self(
            id: $user->getId(),
            name: $user->getName(),
            email: $user->getEmail()
        );
    }
}

// Controller
class UserController extends AbstractController
{
    public function __construct(
        private UserService $userService
    ) {}

    #[Route('/user/{id}', name: 'user_show')]
    public function show(int $id): Response
    {
        $user = $this->userService->getUser($id);

        if ($user === null) {
            throw $this->createNotFoundException('User not found');
        }

        return $this->render('user/show.html.twig', [
            'user' => $user
        ]);
    }

    #[Route('/users/search', name: 'user_search')]
    public function search(Request $request): Response
    {
        $name = $request->query->get('name', '');
        $users = $this->userService->searchByName($name);

        return $this->render('user/search.html.twig', [
            'users' => $users,
            'search' => $name
        ]);
    }
}
```

---

## Global Variables

### `global $db` → Dependency Injection

**Legacy Pattern:**
```php
// database.php - global connection
$db = mysqli_connect("localhost", "root", "", "mydb");

// Using global in functions
function get_user($id) {
    global $db;
    $result = mysqli_query($db, "SELECT * FROM users WHERE id = $id");
    return mysqli_fetch_assoc($result);
}

// Global in classes
class User {
    function get_user($id) {
        global $db;
        $result = mysqli_query($db, "SELECT * FROM users WHERE id = $id");
        return mysqli_fetch_assoc($result);
    }
}

// Multiple globals
function process_order($orderId) {
    global $db, $logger, $config, $cache;

    $order = mysqli_query($db, "SELECT * FROM orders WHERE id = $orderId");
    $logger->log("Processing order: $orderId");
    $cache->set("order_$orderId", $order);
}

// Global state in includes
// config.php
$config = array(
    'db_host' => 'localhost',
    'db_name' => 'mydb',
    'debug' => true
);

// In any file
global $config;
echo $config['debug'];
```

**Modern Symfony Pattern:**
```php
// Entity
#[ORM\Entity]
#[ORM\Table(name: 'users')]
class User
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\Column(type: 'string', length: 255)]
    private string $name;

    // ...
}

// Repository
interface UserRepositoryInterface
{
    public function find(int $id): ?User;
    public function findAll(): array;
    public function save(User $user): void;
}

class UserRepository extends ServiceEntityRepository implements UserRepositoryInterface
{
    public function __construct(RegistryInterface $registry)
    {
        parent::__construct($registry, User::class);
    }

    public function find(int $id): ?User
    {
        return $this->findOneBy(['id' => $id]);
    }

    public function findAll(): array
    {
        return $this->findAll();
    }

    public function save(User $user): void
    {
        $this->getEntityManager()->persist($user);
        $this->getEntityManager()->flush();
    }
}

// Logger Service
interface LoggerInterface
{
    public function log(string $message, array $context = []): void;
    public function error(string $message, array $context = []): void;
}

class Logger implements LoggerInterface
{
    public function __construct(
        private LoggerInterface $logger
    ) {}

    public function log(string $message, array $context = []): void
    {
        $this->logger->info($message, $context);
    }

    public function error(string $message, array $context = []): void
    {
        $this->logger->error($message, $context);
    }
}

// Configuration Service
class ConfigService
{
    private array $config;

    public function __construct(
        #[Autowire('%env(APP_ENV)%')]
        string $env,

        #[Autowire('%kernel.project_dir%')]
        string $projectDir
    ) {
        $this->config = [
            'debug' => $env === 'dev',
            'project_dir' => $projectDir
        ];
    }

    public function get(string $key, mixed $default = null): mixed
    {
        return $this->config[$key] ?? $default;
    }

    public function isDebug(): bool
    {
        return $this->config['debug'];
    }
}

// Cache Service
interface CacheInterface
{
    public function get(string $key, callable $callback, int $ttl = 3600): mixed;
    public function set(string $key, mixed $value, int $ttl = 3600): void;
    public function delete(string $key): void;
}

class CacheService implements CacheInterface
{
    public function __construct(
        private CacheAdapterInterface $cache
    ) {}

    public function get(string $key, callable $callback, int $ttl = 3600): mixed
    {
        $value = $this->cache->get($key);

        if ($value === null) {
            $value = $callback();
            $this->cache->set($key, $value, $ttl);
        }

        return $value;
    }

    public function set(string $key, mixed $value, int $ttl = 3600): void
    {
        $this->cache->set($key, $value, $ttl);
    }

    public function delete(string $key): void
    {
        $this->cache->delete($key);
    }
}

// Application Service - NO GLOBALS, all injected
class OrderService
{
    public function __construct(
        private EntityManagerInterface $entityManager,
        private LoggerInterface $logger,
        private CacheInterface $cache,
        private ConfigService $config,
        private UserRepositoryInterface $userRepository
    ) {}

    public function processOrder(int $orderId): OrderDTO
    {
        $this->logger->log("Processing order: $orderId");

        // Try cache first
        $cacheKey = "order_$orderId";
        $order = $this->cache->get($cacheKey, function () use ($orderId) {
            return $this->entityManager
                ->getRepository(Order::class)
                ->find($orderId);
        });

        if ($order === null) {
            throw new OrderNotFoundException($orderId);
        }

        if ($this->config->isDebug()) {
            $this->logger->log("Order found: " . $order->getId());
        }

        return OrderDTO::fromEntity($order);
    }
}

// Controller
class OrderController extends AbstractController
{
    public function __construct(
        private OrderService $orderService
    ) {}

    #[Route('/order/{id}', name: 'order_show')]
    public function show(int $id): Response
    {
        try {
            $order = $this->orderService->processOrder($id);

            return $this->render('order/show.html.twig', [
                'order' => $order
            ]);
        } catch (OrderNotFoundException $e) {
            throw $this->createNotFoundException($e->getMessage());
        }
    }
}
```

---

## Session Management

### `$_SESSION` → Symfony Session Service

**Legacy Pattern:**
```php
// Starting session
session_start();

// Setting values
$_SESSION['user_id'] = $userId;
$_SESSION['username'] = $username;
$_SESSION['is_logged_in'] = true;
$_SESSION['cart'] = array();
$_SESSION['cart']['items'] = array();

// Getting values
$userId = $_SESSION['user_id'];
$username = $_SESSION['username'];

// Checking session
if (isset($_SESSION['is_logged_in']) && $_SESSION['is_logged_in']) {
    // logged in
}

// Unsetting
unset($_SESSION['user_id']);

// Destroying session
session_destroy();

// Session in functions
function get_current_user() {
    if (isset($_SESSION['user_id'])) {
        return $_SESSION['user_id'];
    }
    return null;
}

// Flash messages (manual)
$_SESSION['flash_message'] = "Success!";
if (isset($_SESSION['flash_message'])) {
    echo $_SESSION['flash_message'];
    unset($_SESSION['flash_message']);
}

// Shopping cart in session
$_SESSION['cart'] = array(
    'items' => array(
        'product_1' => array('qty' => 2, 'price' => 19.99),
        'product_2' => array('qty' => 1, 'price' => 49.99)
    ),
    'total' => 89.97
);
```

**Modern Symfony Pattern:**
```php
// Session Service
class SessionService
{
    public function __construct(
        private SessionInterface $session
    ) {}

    public function set(string $key, mixed $value): void
    {
        $this->session->set($key, $value);
    }

    public function get(string $key, mixed $default = null): mixed
    {
        return $this->session->get($key, $default);
    }

    public function has(string $key): bool
    {
        return $this->session->has($key);
    }

    public function remove(string $key): void
    {
        $this->session->remove($key);
    }

    // Flash messages
    public function addFlash(string $type, string $message): void
    {
        $this->session->getFlashBag()->add($type, $message);
    }

    public function getFlashes(string $type = null): array
    {
        if ($type !== null) {
            return $this->session->getFlashBag()->get($type);
        }
        return $this->session->getFlashBag()->all();
    }
}

// Authentication Service
class AuthenticationService
{
    public function __construct(
        private TokenStorageInterface $tokenStorage,
        private UserRepositoryInterface $userRepository,
        private SessionInterface $session,
        private GuardAuthenticatorInterface $guard
    ) {}

    public function login(string $email, string $password): bool
    {
        $user = $this->userRepository->findByEmail($email);

        if ($user === null || !password_verify($password, $user->getPassword())) {
            return false;
        }

        $token = new UsernamePasswordToken(
            $user,
            $password,
            'main',
            $user->getRoles()
        );

        $this->tokenStorage->setToken($token);

        return true;
    }

    public function logout(): void
    {
        $this->tokenStorage->setToken(null);
        $this->session->invalidate();
    }

    public function getCurrentUser(): ?UserInterface
    {
        $token = $this->tokenStorage->getToken();
        if ($token === null) {
            return null;
        }

        $user = $token->getUser();
        return $user instanceof UserInterface ? $user : null;
    }

    public function isLoggedIn(): bool
    {
        return $this->getCurrentUser() !== null;
    }
}

// Cart Service (replaces session-based cart)
class CartService
{
    private const CART_KEY = 'shopping_cart';

    public function __construct(
        private SessionInterface $session,
        private ProductRepositoryInterface $productRepository
    ) {}

    public function addItem(int $productId, int $quantity = 1): CartDTO
    {
        $cart = $this->getCart();

        if (isset($cart[$productId])) {
            $cart[$productId] += $quantity;
        } else {
            $cart[$productId] = $quantity;
        }

        $this->session->set(self::CART_KEY, $cart);

        return $this->getCartDTO();
    }

    public function removeItem(int $productId): void
    {
        $cart = $this->getCart();
        unset($cart[$productId]);
        $this->session->set(self::CART_KEY, $cart);
    }

    public function clear(): void
    {
        $this->session->remove(self::CART_KEY);
    }

    public function getCart(): array
    {
        return $this->session->get(self::CART_KEY, []);
    }

    public function getCartDTO(): CartDTO
    {
        $cart = $this->getCart();
        $items = [];
        $total = 0.0;

        foreach ($cart as $productId => $quantity) {
            $product = $this->productRepository->find($productId);

            if ($product !== null) {
                $itemTotal = $product->getPrice() * $quantity;
                $total += $itemTotal;

                $items[] = new CartItemDTO(
                    productId: $product->getId(),
                    name: $product->getName(),
                    price: $product->getPrice(),
                    quantity: $quantity,
                    total: $itemTotal
                );
            }
        }

        return new CartDTO(items: $items, total: $total);
    }
}

// Controller
class AuthController extends AbstractController
{
    public function __construct(
        private AuthenticationService $authService,
        private SessionService $sessionService
    ) {}

    #[Route('/login', name: 'login', methods: ['GET', 'POST'])]
    public function login(Request $request): Response
    {
        if ($request->isMethod('POST')) {
            $email = $request->request->get('email');
            $password = $request->request->get('password');

            if ($this->authService->login($email, $password)) {
                $this->sessionService->addFlash('success', 'Welcome back!');
                return $this->redirectToRoute('dashboard');
            }

            $this->sessionService->addFlash('error', 'Invalid credentials');
        }

        return $this->render('auth/login.html.twig');
    }

    #[Route('/logout', name: 'logout')]
    public function logout(): Response
    {
        $this->authService->logout();
        $this->sessionService->addFlash('info', 'You have been logged out');

        return $this->redirectToRoute('home');
    }
}

class CartController extends AbstractController
{
    public function __construct(
        private CartService $cartService,
        private SessionService $sessionService
    ) {}

    #[Route('/cart', name: 'cart_show')]
    public function show(): Response
    {
        $cart = $this->cartService->getCartDTO();

        return $this->render('cart/show.html.twig', [
            'cart' => $cart
        ]);
    }

    #[Route('/cart/add/{productId}', name: 'cart_add')]
    public function add(int $productId, Request $request): Response
    {
        $quantity = (int) $request->request->get('quantity', 1);
        $this->cartService->addItem($productId, $quantity);

        $this->sessionService->addFlash('success', 'Item added to cart');

        return $this->redirectToRoute('cart_show');
    }
}
```

---

## Include/Require Chains

### `include` / `require` → Service Autowiring

**Legacy Pattern:**
```php
// config.php
<?php
define('DB_HOST', 'localhost');
define('DB_USER', 'root');
define('DB_PASS', '');
define('DB_NAME', 'mydb');
define('BASE_PATH', '/var/www/html');
define('DEBUG', true);

// functions.php
<?php
function db_connect() {
    return mysqli_connect(DB_HOST, DB_USER, DB_PASS, DB_NAME);
}

function sanitize($input) {
    return htmlspecialchars($input, ENT_QUOTES, 'UTF-8');
}

function format_date($date) {
    return date('Y-m-d', strtotime($date));
}

// header.php - common across all pages
<?php
require_once 'config.php';
require_once 'functions.php';

session_start();

$conn = db_connect();
$user = isset($_SESSION['user_id']) ? get_user($_SESSION['user_id']) : null;
?>

// index.php - nested includes
<?php
require_once 'header.php';

$page = $_GET['page'] ?? 'home';

switch($page) {
    case 'products':
        require_once 'products.php';
        break;
    case 'orders':
        require_once 'orders.php';
        break;
    default:
        require_once 'home.php';
}

require_once 'footer.php';
?>

// products.php - deep nesting
<?php
require_once 'config.php';
require_once 'functions.php';
require_once 'header.php';

$products = mysqli_query($conn, "SELECT * FROM products");

while ($product = mysqli_fetch_assoc($products)) {
    include 'product_item.php';
}
?>

// product_item.php - partial template
<div class="product">
    <h3><?php echo sanitize($product['name']); ?></h3>
    <p><?php echo $product['price']; ?></p>
</div>
```

**Modern Symfony Pattern:**
```php
# config/services.yaml
services:
    _defaults:
        autowire: true
        autoconfigure: true
        public: false

    # Configuration as service parameters
    App\Application\Config\Config:
        arguments:
            $dbHost: '%env(DB_HOST)%'
            $dbUser: '%env(DB_USER)%'
            $dbPass: '%env(DB_PASS)%'
            $dbName: '%env(DB_NAME)%'
            $basePath: '%kernel.project_dir%'
            $debug: '%env(bool:APP_DEBUG)%'

    # Services are automatically registered via autowiring
    App\Application\Database\DatabaseService: ~

    App\Application\Helper\SanitizeHelper: ~

    App\Application\Helper\DateHelper: ~

    # Controllers are automatically registered
    App\Infrastructure\Controller\ProductsController:
        tags: ['controller.service_arguments']

// Configuration Service (replaces config.php)
class Config
{
    private string $dbHost;
    private string $dbUser;
    private string $dbPass;
    private string $dbName;
    private string $basePath;
    private bool $debug;

    public function __construct(
        string $dbHost,
        string $dbUser,
        string $dbPass,
        string $dbName,
        string $basePath,
        bool $debug
    ) {
        $this->dbHost = $dbHost;
        $this->dbUser = $dbUser;
        $this->dbPass = $dbPass;
        $this->dbName = $dbName;
        $this->basePath = $basePath;
        $this->debug = $debug;
    }

    public function getDbHost(): string { return $this->dbHost; }
    public function getDbUser(): string { return $this->dbUser; }
    public function getDbPass(): string { return $this->dbPass; }
    public function getDbName(): string { return $this->dbName; }
    public function getBasePath(): string { return $this->basePath; }
    public function isDebug(): bool { return $this->debug; }
}

// Database Service (replaces functions.php db_connect)
class DatabaseService
{
    public function __construct(
        private Config $config
    ) {}

    public function connect(): Connection
    {
        return DriverManager::getConnection([
            'host' => $this->config->getDbHost(),
            'user' => $this->config->getDbUser(),
            'password' => $this->config->getDbPass(),
            'database' => $this->config->getDbName(),
            'driver' => 'pdo_mysql'
        ]);
    }
}

// Sanitize Helper (replaces functions.php sanitize)
class SanitizeHelper
{
    public function sanitize(string $input): string
    {
        return htmlspecialchars($input, ENT_QUOTES, 'UTF-8');
    }

    public function sanitizeHtml(Symfony\Component\HtmlSanitizer\HtmlSanitizerInterface $sanitizer, string $input): string
    {
        return $sanitizer->sanitize($input);
    }
}

// Date Helper (replaces functions.php format_date)
class DateHelper
{
    public function format(DateTimeInterface $date, string $format = 'Y-m-d'): string
    {
        return $date->format($format);
    }

    public function now(): DateTimeImmutable
    {
        return new DateTimeImmutable();
    }
}

// Controller with autowired dependencies
class ProductsController extends AbstractController
{
    public function __construct(
        private ProductRepositoryInterface $productRepository,
        private SanitizeHelper $sanitizeHelper,
        private DateHelper $dateHelper,
        private Config $config
    ) {}

    #[Route('/products', name: 'products_index')]
    public function index(): Response
    {
        $products = $this->productRepository->findAll();

        return $this->render('products/index.html.twig', [
            'products' => $products,
            'debug' => $this->config->isDebug()
        ]);
    }

    #[Route('/products/{id}', name: 'products_show')]
    public function show(int $id): Response
    {
        $product = $this->productRepository->find($id);

        if ($product === null) {
            throw $this->createNotFoundException('Product not found');
        }

        return $this->render('products/show.html.twig', [
            'product' => $product,
            'formatted_date' => $this->dateHelper->format($product->getCreatedAt())
        ]);
    }
}

// Twig templates (replaces PHP includes)
{# templates/products/index.html.twig #}
{% extends 'base.html.twig' %}

{% block body %}
<h1>Products</h1>

<div class="products">
    {% for product in products %}
        <div class="product">
            <h3>{{ product.name|e }}</h3>
            <p>${{ product.price }}</p>
            <a href="{{ path('products_show', {id: product.id}) }}">View</a>
        </div>
    {% endfor %}
</div>

{% if debug %}
    <p class="debug">Debug mode is enabled</p>
{% endif %}
{% endblock %}
```

---

## Configuration with `define()`

### `define()` → `.env` + Kernel Parameters

**Legacy Pattern:**
```php
// constants.php
<?php
define('DB_HOST', 'localhost');
define('DB_PORT', 3306);
define('DB_USER', 'root');
define('DB_PASS', 'secret');
define('DB_NAME', 'myapp');

define('SITE_NAME', 'My Application');
define('SITE_URL', 'http://localhost:8080');

define('TIMEZONE', 'America/New_York');
define('DEBUG', true);
define('LOG_LEVEL', 'DEBUG');

define('UPLOAD_PATH', '/var/www/html/uploads');
define('MAX_UPLOAD_SIZE', 10485760); // 10MB
define('ALLOWED_EXTENSIONS', 'jpg,png,gif,pdf');

define('SESSION_TIMEOUT', 3600);
define('COOKIE_DOMAIN', '.example.com');

define('EMAIL_FROM', 'noreply@example.com');
define('EMAIL_SMTP_HOST', 'smtp.mailtrap.io');
define('EMAIL_SMTP_PORT', 2525);

// Using constants
$conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS, DB_NAME);
if (DEBUG) {
    echo mysqli_error($conn);
}

date_default_timezone_set(TIMEZONE);

// Checking defined
if (defined('DEBUG') && DEBUG) {
    error_reporting(E_ALL);
}
```

**Modern Symfony Pattern:**
```php
# .env
DATABASE_URL="mysql://root:secret@127.0.0.1:3306/myapp?serverVersion=8.0"
APP_ENV=dev
APP_SECRET=your-secret-key-here
APP_TIMEZONE=America/New_York

# Upload configuration
UPLOAD_PATH=/var/www/html/uploads
MAX_UPLOAD_SIZE=10485760

# Email configuration
MAILER_DSN=smtp://user:pass@mailtrap.io:2525

# config/packages/doctrine.yaml
doctrine:
    dbal:
        url: '%env(DATABASE_URL)%'
        options:
            charset: utf8mb4

# config/packages/framework.yaml
framework:
    secret: '%env(APP_SECRET)%'
    timezone: '%env(APP_TIMEZONE)%'
    session:
        handler_id: session.handler.native_file
        cookie_domain: '%env(COOKIE_DOMAIN)%'

# config/packages/security.yaml
security:
    firewalls:
        main:
            logout:
                path: app_logout
                target: /login

# config/services.yaml
parameters:
    app.site_name: 'My Application'
    app.site_url: '%env(SITE_URL)%'
    app.upload_path: '%env(UPLOAD_PATH)%'
    app.max_upload_size: '%env(int:MAX_UPLOAD_SIZE)%'
    app.allowed_extensions: '%env(ALLOWED_EXTENSIONS)%'
    app.session_timeout: 3600
    app.email_from: '%env(EMAIL_FROM)%'

services:
    App\Application\Config\AppConfig:
        arguments:
            $siteName: '%app.site_name%'
            $siteUrl: '%app.site_url%'
            $uploadPath: '%app.upload_path%'
            $maxUploadSize: '%app.max_upload_size%'
            $allowedExtensions: !php/const:explode(',', '%app.allowed_extensions%')
            $sessionTimeout: '%app.session_timeout%'

    App\Application\Upload\UploadService:
        arguments:
            $uploadPath: '%app.upload_path%'
            $maxUploadSize: '%app.max_upload_size%'
            $allowedExtensions: '%app.allowed_extensions%'

    App\Application\Email\EmailService:
        arguments:
            $fromEmail: '%app.email_from%'
            $mailerDsn: '%env(MAILER_DSN)%'

// AppConfig Service
class AppConfig
{
    public function __construct(
        private string $siteName,
        private string $siteUrl,
        private string $uploadPath,
        private int $maxUploadSize,
        private array $allowedExtensions,
        private int $sessionTimeout
    ) {}

    public function getSiteName(): string { return $this->siteName; }
    public function getSiteUrl(): string { return $this->siteUrl; }
    public function getUploadPath(): string { return $this->uploadPath; }
    public function getMaxUploadSize(): int { return $this->maxUploadSize; }
    public function getAllowedExtensions(): array { return $this->allowedExtensions; }
    public function getSessionTimeout(): int { return $this->sessionTimeout; }
}

// Upload Service
class UploadService
{
    public function __construct(
        private string $uploadPath,
        private int $maxUploadSize,
        private array $allowedExtensions
    ) {}

    public function upload(UploadedFile $file): ?string
    {
        if ($file->getSize() > $this->maxUploadSize) {
            throw new UploadException('File too large');
        }

        $extension = $file->getClientOriginalExtension();
        if (!in_array($extension, $this->allowedExtensions)) {
            throw new UploadException('Invalid file type');
        }

        $filename = sprintf('%s_%s.%s',
            time(),
            bin2hex(random_bytes(8)),
            $extension
        );

        $file->move($this->uploadPath, $filename);

        return $filename;
    }
}

// Controller using config
class UploadController extends AbstractController
{
    public function __construct(
        private UploadService $uploadService,
        private AppConfig $appConfig
    ) {}

    #[Route('/upload', name: 'upload', methods: ['GET', 'POST'])]
    public function upload(Request $request): Response
    {
        $form = $this->createForm(UploadType::class);

        $form->handleRequest($request);

        if ($form->isSubmitted() && $form->isValid()) {
            /** @var UploadedFile $file */
            $file = $form->get('file')->getData();

            try {
                $filename = $this->uploadService->upload($file);
                $this->addFlash('success', 'File uploaded successfully');

                return $this->redirectToRoute('upload_success', ['filename' => $filename]);
            } catch (UploadException $e) {
                $this->addFlash('error', $e->getMessage());
            }
        }

        return $this->render('upload/form.html.twig', [
            'form' => $form->createView(),
            'max_size' => $this->appConfig->getMaxUploadSize(),
            'allowed' => implode(', ', $this->appConfig->getAllowedExtensions())
        ]);
    }
}
```

---

## Summary Table

| Generic PHP Pattern | Symfony Hexagonal Equivalent |
|---------------------|------------------------------|
| `mysql_query()` | Doctrine DBAL |
| `mysqli_query()` | Doctrine QueryBuilder / Repository |
| `global $db` | Dependency Injection |
| `global $logger` | LoggerInterface |
| `$_SESSION` | SessionInterface |
| `session_start()` | Framework session config |
| `include/require` | Service autowiring + Twig templates |
| `require_once` | Service definitions + imports |
| `define()` | `.env` + ParameterBag |
| `date_default_timezone_set()` | Framework timezone config |
| `mysqli_connect()` | Doctrine Connection |
| `$_GET/$_POST` | Request object |
| `header()` | RedirectResponse |
| `echo` / `print` | Twig templates |

---

## Anti-Patterns to Avoid

1. **Direct MySQL Functions** — Use Doctrine ORM with repositories
2. **Global Variables** — Inject all dependencies via constructor
3. **Raw `$_SESSION`** — Use Symfony Session service
4. **Include Chains** — Use autowiring and Twig inheritance
5. **`define()` Constants** — Use environment variables + ParameterBag
6. **Raw SQL Queries** — Use QueryBuilder or DQL
7. **Global DB Connection** — Use EntityManager via DI
8. **PHP in Templates** — Use Twig exclusively
9. **Manual Session Management** — Use Symfony session handling
10. **Hardcoded Paths** — Use `%kernel.project_dir%` parameter