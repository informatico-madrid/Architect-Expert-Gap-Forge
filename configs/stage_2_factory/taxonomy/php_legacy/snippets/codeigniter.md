# CodeIgniter Anti-Patterns Mapping

This document provides specific modernization patterns for CodeIgniter legacy PHP applications, mapping common CI patterns to their Symfony hexagonal architecture equivalents.

## Database Access Patterns

### `$this->db->query()` → Doctrine DBAL

**Legacy Pattern:**
```php
// Simple query
$result = $this->db->query("SELECT * FROM users WHERE id = ?", array($userId));

// Query with active record
$query = $this->db->get('products');
$products = $query->result();

$query = $this->db->select('id, name, price')
    ->from('products')
    ->where('status', 'active')
    ->like('name', 'search term')
    ->order_by('price', 'DESC')
    ->limit(10, 0)
    ->get();

// Insert
$data = array(
    'name' => 'Product Name',
    'price' => 99.99,
    'status' => 'active'
);
$this->db->insert('products', $data);

// Update
$this->db->where('id', $productId);
$this->db->update('products', $data);

// Delete
$this->db->where('id', $productId);
$this->db->delete('products');

// Raw query
$sql = "SELECT p.*, c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.status = 'active'";
$query = $this->db->query($sql);
$results = $query->result_array();

// Transactions
$this->db->trans_start();
$this->db->query('INSERT INTO orders...');
$this->db->query('INSERT INTO order_items...');
$this->db->trans_complete();
```

**Modern Symfony Pattern:**
```php
// Entity
#[ORM\Entity]
#[ORM\Table(name: 'products')]
class Product
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\Column(type: 'string', length: 255)]
    private string $name;

    #[ORM\Column(type: 'decimal', precision: 10, scale: 2)]
    private float $price;

    #[ORM\Column(type: 'string', length: 50)]
    private string $status = 'active';

    #[ORM\ManyToOne(targetEntity: Category::class, inversedBy: 'products')]
    #[ORM\JoinColumn(name: 'category_id', referencedColumnName: 'id')]
    private ?Category $category = null;

    #[ORM\Column(type: 'datetime')]
    private ?DateTimeInterface $createdAt = null;

    #[ORM\Column(type: 'datetime')]
    private ?DateTimeInterface $updatedAt = null;

    // Getters and setters...
}

// Repository (Driven Adapter)
class ProductRepository extends ServiceEntityRepository implements ProductRepositoryInterface
{
    public function __construct(RegistryInterface $registry)
    {
        parent::__construct($registry, Product::class);
    }

    public function find(int $id): ?Product
    {
        return $this->findOneBy(['id' => $id]);
    }

    public function findAll(): array
    {
        return $this->findBy(['status' => 'active'], ['name' => 'ASC']);
    }

    public function findActive(): array
    {
        return $this->createQueryBuilder('p')
            ->andWhere('p.status = :status')
            ->setParameter('status', 'active')
            ->orderBy('p.name', 'ASC')
            ->getQuery()
            ->getResult();
    }

    public function search(string $term, int $limit = 10): array
    {
        return $this->createQueryBuilder('p')
            ->andWhere('p.status = :status')
            ->andWhere('p.name LIKE :term')
            ->setParameter('status', 'active')
            ->setParameter('term', "%{$term}%")
            ->orderBy('p.price', 'DESC')
            ->setMaxResults($limit)
            ->getQuery()
            ->getResult();
    }

    public function findByCategory(int $categoryId): array
    {
        return $this->createQueryBuilder('p')
            ->andWhere('p.category = :categoryId')
            ->setParameter('categoryId', $categoryId)
            ->getQuery()
            ->getResult();
    }

    public function save(Product $product): void
    {
        $this->getEntityManager()->persist($product);
        $this->getEntityManager()->flush();
    }

    public function remove(Product $product): void
    {
        $this->getEntityManager()->remove($product);
        $this->getEntityManager()->flush();
    }
}

// Application Service with Transaction Support
class ProductService
{
    public function __construct(
        private ProductRepositoryInterface $productRepository,
        private EntityManagerInterface $entityManager
    ) {}

    public function getProduct(int $id): ?ProductDTO
    {
        $product = $this->productRepository->find($id);
        return $product ? ProductDTO::fromEntity($product) : null;
    }

    public function searchProducts(string $term, int $limit = 10): array
    {
        return array_map(
            fn(Product $p) => ProductDTO::fromEntity($p),
            $this->productRepository->search($term, $limit)
        );
    }

    public function createProduct(CreateProductDTO $dto): ProductDTO
    {
        $product = new Product();
        $product->setName($dto->name);
        $product->setPrice($dto->price);
        $product->setStatus($dto->status ?? 'active');

        $this->productRepository->save($product);

        return ProductDTO::fromEntity($product);
    }

    public function updateProduct(int $id, UpdateProductDTO $dto): ?ProductDTO
    {
        $product = $this->productRepository->find($id);

        if ($product === null) {
            return null;
        }

        if ($dto->name !== null) {
            $product->setName($dto->name);
        }
        if ($dto->price !== null) {
            $product->setPrice($dto->price);
        }

        $this->productRepository->save($product);

        return ProductDTO::fromEntity($product);
    }

    public function deleteProduct(int $id): bool
    {
        $product = $this->productRepository->find($id);

        if ($product === null) {
            return false;
        }

        $this->productRepository->remove($product);
        return true;
    }

    public function createOrderWithItems(OrderDTO $orderDto): Order
    {
        return $this->entityManager->transactional(function (EntityManagerInterface $em) use ($orderDto) {
            $order = new Order();
            $order->setCustomerId($orderDto->customerId);
            $order->setStatus('pending');

            $em->persist($order);

            foreach ($orderDto->items as $itemDto) {
                $item = new OrderItem();
                $item->setOrder($order);
                $item->setProductId($itemDto->productId);
                $item->setQuantity($itemDto->quantity);
                $item->setPrice($itemDto->price);

                $em->persist($item);
            }

            $em->flush();
            return $order;
        });
    }
}

// Controller
class ProductController extends AbstractController
{
    public function __construct(
        private ProductService $productService
    ) {}

    #[Route('/products', name: 'product_list')]
    public function list(Request $request): Response
    {
        $term = $request->query->get('search', '');
        $limit = (int) $request->query->get('limit', 10);

        $products = $this->productService->searchProducts($term, $limit);

        return $this->render('product/list.html.twig', [
            'products' => $products
        ]);
    }

    #[Route('/product/{id}', name: 'product_show')]
    public function show(int $id): Response
    {
        $product = $this->productService->getProduct($id);

        if ($product === null) {
            throw $this->createNotFoundException('Product not found');
        }

        return $this->render('product/show.html.twig', [
            'product' => $product
        ]);
    }
}
```

---

### `$this->load->model()` → Dependency Injection

**Legacy Pattern:**
```php
// Loading model in controller
$this->load->model('User_model', 'User');

$user = $this->User->get($userId);
$users = $this->User->get_all();

// Model with dependencies (god object pattern)
class User_model extends CI_Model
{
    public function get($id)
    {
        // Direct DB access
        $query = $this->db->get_where('users', array('id' => $id));
        return $query->row();
    }

    public function get_all()
    {
        $query = $this->db->get('users');
        return $query->result();
    }

    public function insert($data)
    {
        $this->db->insert('users', $data);
        return $this->db->insert_id();
    }

    // Model loading another model
    public function get_with_orders($userId)
    {
        $this->load->model('Order_model', 'Order');
        $user = $this->get($userId);
        $user->orders = $this->Order->get_by_user($userId);
        return $user;
    }
}

// In controller
class User extends CI_Controller
{
    function profile($id)
    {
        $this->load->model('user_model');
        $data['user'] = $this->user_model->get($id);
        $this->load->view('user/profile', $data);
    }
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

    #[ORM\Column(type: 'string', length: 255, unique: true)]
    private string $email;

    #[ORM\Column(type: 'string', length: 255)]
    private string $name;

    #[ORM\Column(type: 'datetime')]
    private ?DateTimeInterface $createdAt = null;

    #[ORM\OneToMany(mappedBy: 'user', targetEntity: Order::class)]
    private Collection $orders;

    public function __construct()
    {
        $this->orders = new ArrayCollection();
    }

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

// Application Service (Use Case)
class UserService
{
    public function __construct(
        private UserRepositoryInterface $userRepository,
        private OrderRepositoryInterface $orderRepository
    ) {}

    public function getUser(int $id): ?UserDTO
    {
        $user = $this->userRepository->find($id);
        return $user ? UserDTO::fromEntity($user) : null;
    }

    public function getUserWithOrders(int $userId): ?UserWithOrdersDTO
    {
        $user = $this->userRepository->find($userId);

        if ($user === null) {
            return null;
        }

        $orders = $this->orderRepository->findByUser($userId);

        return UserWithOrdersDTO::fromEntity($user, $orders);
    }

    public function createUser(CreateUserDTO $dto): UserDTO
    {
        // Check if email exists
        if ($this->userRepository->findByEmail($dto->email) !== null) {
            throw new UserAlreadyExistsException($dto->email);
        }

        $user = new User();
        $user->setEmail($dto->email);
        $user->setName($dto->name);

        $this->userRepository->save($user);

        return UserDTO::fromEntity($user);
    }
}

// Controller with DI
class UserController extends AbstractController
{
    public function __construct(
        private UserService $userService
    ) {}

    #[Route('/user/{id}', name: 'user_profile')]
    public function profile(int $id): Response
    {
        $user = $this->userService->getUser($id);

        if ($user === null) {
            throw $this->createNotFoundException('User not found');
        }

        return $this->render('user/profile.html.twig', [
            'user' => $user
        ]);
    }

    #[Route('/user/{id}/orders', name: 'user_orders')]
    public function orders(int $id): Response
    {
        $userWithOrders = $this->userService->getUserWithOrders($id);

        if ($userWithOrders === null) {
            throw $this->createNotFoundException('User not found');
        }

        return $this->render('user/orders.html.twig', [
            'user' => $userWithOrders
        ]);
    }
}
```

---

## Session Management

### `$this->session->userdata()` → Symfony Session Service

**Legacy Pattern:**
```php
// Set session data
$this->session->set_userdata('user_id', $userId);
$this->session->set_userdata('user_name', $username);
$this->session->set_userdata('is_logged_in', true);

// Get session data
$userId = $this->session->userdata('user_id');
$username = $this->session->userdata('user_name');

// Get all session data
$sessionData = $this->session->all_userdata();

// Flash data (one-time session data)
$this->session->set_flashdata('message', 'Success!');
$message = $this->session->flashdata('message');

// Session in model
class Cart_model extends CI_Model
{
    function add_to_cart($productId, $quantity)
    {
        $cart = $this->session->userdata('cart');

        if (!is_array($cart)) {
            $cart = array();
        }

        if (isset($cart[$productId])) {
            $cart[$productId] += $quantity;
        } else {
            $cart[$productId] = $quantity;
        }

        $this->session->set_userdata('cart', $cart);
    }

    function get_cart()
    {
        return $this->session->userdata('cart');
    }

    function clear_cart()
    {
        $this->session->unset_userdata('cart');
    }
}
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

    public function remove(string $key): void
    {
        $this->session->remove($key);
    }

    public function has(string $key): bool
    {
        return $this->session->has($key);
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

// Authentication Service with TokenStorage
class AuthenticationService
{
    public function __construct(
        private TokenStorageInterface $tokenStorage,
        private UserRepositoryInterface $userRepository,
        private SessionInterface $session
    ) {}

    public function login(string $email, string $password): bool
    {
        $user = $this->userRepository->findByEmail($email);

        if ($user === null) {
            return false;
        }

        if (!password_verify($password, $user->getPassword())) {
            return false;
        }

        $token = new UsernamePasswordToken(
            $user,
            $password,
            'main',
            $user->getRoles()
        );

        $this->tokenStorage->setToken($token);

        // Store additional data in session
        $this->session->set('user_id', $user->getId());
        $this->session->set('user_name', $user->getName());

        return true;
    }

    public function logout(): void
    {
        $this->tokenStorage->setToken(null);
        $this->session->clear();
    }

    public function getCurrentUser(): ?UserInterface
    {
        $token = $this->tokenStorage->getToken();

        if ($token === null) {
            return null;
        }

        $user = $token->getUser();

        if ($user instanceof UserInterface) {
            return $user;
        }

        return null;
    }

    public function isLoggedIn(): bool
    {
        return $this->getCurrentUser() !== null;
    }
}

// Cart Service (replaces CI session-based cart)
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

    public function removeItem(int $productId): CartDTO
    {
        $cart = $this->getCart();
        unset($cart[$productId]);
        $this->session->set(self::CART_KEY, $cart);

        return $this->getCartDTO();
    }

    public function updateQuantity(int $productId, int $quantity): CartDTO
    {
        $cart = $this->getCart();

        if ($quantity <= 0) {
            unset($cart[$productId]);
        } else {
            $cart[$productId] = $quantity;
        }

        $this->session->set(self::CART_KEY, $cart);

        return $this->getCartDTO();
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
                $this->sessionService->addFlash('success', 'Login successful!');
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
        private CartService $cartService
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
        $cart = $this->cartService->addItem($productId, $quantity);

        return $this->redirectToRoute('cart_show');
    }
}
```

---

## Helper Functions

### CI Helpers → Symfony Services

**Legacy Pattern:**
```php
// URL Helper
redirect('/products/view/' . $productId);
site_url('controller/method');
base_url('assets/css/style.css');
anchor('controller/method', 'Link Text');
anchor('controller/method/'.$id, 'Edit', 'class="btn"');

// Form Helper
$attributes = array('class' => 'form-horizontal', 'id' => 'myform');
echo form_open('controller/method', $attributes);
echo form_input('username', set_value('username'));
echo form_password('password');
echo form_submit('submit', 'Login');
echo form_close();

// String Helper
$slug = url_title('My Product Title', 'dash', true);
$truncated = character_limiter($long_string, 100);
$ Excerpt = word_limiter($text, 50);

// Date Helper
$formatted = date('Y-m-d H:i:s');
$human = timespan($timestamp);

// Security Helper
$clean = $this->security->xss_clean($input);
$hash = $this->security->get_csrf_hash();
$token = $this->security->get_csrf_token_name();

// File Helper
$content = read_file('./path/to/file.php');
write_file('./path/to/file.php', $content);

// Creating URL helpers for custom use
function product_url($productId, $productName)
{
    $slug = url_title($productName, 'dash', true);
    return site_url('product/view/' . $productId . '/' . $slug);
}
```

**Modern Symfony Pattern:**
```php
# config/packages/twig.yaml
twig:
    globals:
        # URL helpers as Twig functions
        url_helper: '@App\Infrastructure\Twig\UrlHelperExtension'

// URL Helper Service
class UrlHelperService
{
    public function __construct(
        private RouterInterface $router,
        private UrlGeneratorInterface $urlGenerator
    ) {}

    public function generate(string $route, array $params = []): string
    {
        return $this->urlGenerator->generate($route, $params, UrlGeneratorInterface::ABSOLUTE_URL);
    }

    public function to(string $path): string
    {
        return $path;
    }

    public function asset(string $path): string
    {
        return $this->urlGenerator->generate('asset', ['path' => ltrim($path, '/')], UrlGeneratorInterface::ABSOLUTE_URL);
    }

    public function toProduct(int $id, string $name): string
    {
        $slug = Str::slug($name);
        return $this->generate('product_view', ['id' => $id, 'slug' => $slug]);
    }
}

// Form Service
class FormService
{
    public function __construct(
        private FormFactoryInterface $formFactory,
        private RouterInterface $router
    ) {}

    public function createProductForm(?Product $product = null): FormInterface
    {
        return $this->formFactory->create(ProductType::class, $product);
    }

    public function handleRequest(FormInterface $form, Request $request): bool
    {
        $form->handleRequest($request);
        return $form->isSubmitted() && $form->isValid();
    }

    public function getErrorsAsArray(FormInterface $form): array
    {
        $errors = [];
        foreach ($form->getErrors(true, true) as $error) {
            $errors[] = $error->getMessage();
        }
        return $errors;
    }
}

// Twig Extension for URL helpers
class UrlHelperExtension extends AbstractExtension
{
    public function __construct(
        private RouterInterface $router
    ) {}

    public function getFunctions(): array
    {
        return [
            new TwigFunction('site_url', [$this, 'siteUrl']),
            new TwigFunction('base_url', [$this, 'baseUrl']),
            new TwigFunction('asset_url', [$this, 'assetUrl']),
            new TwigFunction('product_link', [$this, 'productLink']),
        ];
    }

    public function siteUrl(string $route, array $params = []): string
    {
        return $this->router->generate($route, $params);
    }

    public function baseUrl(string $path = ''): string
    {
        return rtrim($this->router->generate('asset', ['path' => ltrim($path, '/')]), '/');
    }

    public function assetUrl(string $path): string
    {
        return $this->router->generate('asset', ['path' => ltrim($path, '/')]);
    }

    public function productLink(int $id, string $name): string
    {
        $slug = Str::slug($name);
        return $this->router->generate('product_view', ['id' => $id, 'slug' => $slug]);
    }
}

// Security Service (replaces CI security helper)
class SecurityService
{
    public function __construct(
        private CsrfTokenManagerInterface $csrfTokenManager
    ) {}

    public function getCsrfToken(string $tokenId): CsrfToken
    {
        return $this->csrfTokenManager->getToken($tokenId);
    }

    public function isCsrfTokenValid(string $tokenId, string $token): bool
    {
        return $this->csrfTokenManager->isTokenValid(
            new CsrfToken($tokenId, $token)
        );
    }

    public function sanitize(string $input): string
    {
        // Use Symfony's built-in sanitizers
        return htmlspecialchars($input, ENT_QUOTES, 'UTF-8');
    }
}

// String Helper Service
class StringHelperService
{
    public function slug(string $text): string
    {
        return Str::slug($text);
    }

    public function limit(int $length, string $text, string $suffix = '...'): string
    {
        return Str::limit($text, $length, $suffix);
    }

    public function words(int $count, string $text, string $suffix = '...'): string
    {
        return Str::words($text, $count, $suffix);
    }

    public function excerpt(string $text, int $length = 100): string
    {
        return $this->limit($length, strip_tags($text));
    }
}

// Date/Time Service (replaces CI date helper)
class DateTimeService
{
    public function now(): DateTimeImmutable
    {
        return new DateTimeImmutable();
    }

    public function format(DateTimeInterface $date, string $format): string
    {
        return $date->format($format);
    }

    public function humanReadable(DateTimeInterface $date): string
    {
        return $this->format($date, 'Y-m-d H:i:s');
    }

    public function timeAgo(DateTimeInterface $date): string
    {
        $now = new DateTimeImmutable();
        $interval = $now->diff($date);

        if ($interval->y > 0) {
            return $interval->y . ' year' . ($interval->y > 1 ? 's' : '') . ' ago';
        }
        if ($interval->m > 0) {
            return $interval->m . ' month' . ($interval->m > 1 ? 's' : '') . ' ago';
        }
        if ($interval->d > 0) {
            return $interval->d . ' day' . ($interval->d > 1 ? 's' : '') . ' ago';
        }
        if ($interval->h > 0) {
            return $interval->h . ' hour' . ($interval->h > 1 ? 's' : '') . ' ago';
        }
        if ($interval->i > 0) {
            return $interval->i . ' minute' . ($interval->i > 1 ? 's' : '') . ' ago';
        }

        return 'just now';
    }
}

// Controller with modern patterns
class ProductController extends AbstractController
{
    public function __construct(
        private ProductService $productService,
        private FormService $formService,
        private SecurityService $securityService
    ) {}

    #[Route('/product/create', name: 'product_create', methods: ['GET', 'POST'])]
    public function create(Request $request): Response
    {
        $form = $this->formService->createProductForm();

        if ($this->formService->handleRequest($form, $request)) {
            $product = $form->getData();
            $this->productService->saveProduct($product);

            $this->addFlash('success', 'Product created successfully');
            return $this->redirectToRoute('product_list');
        }

        return $this->render('product/create.html.twig', [
            'form' => $form->createView()
        ]);
    }
}
```

---

## Configuration & Environment

### CI Config → Symfony Parameters

**Legacy Pattern:**
```php
// config/database.php
$db['default'] = array(
    'dsn' => '',
    'hostname' => 'localhost',
    'username' => 'root',
    'password' => '',
    'database' => 'ci_app',
    'dbdriver' => 'mysqli',
    'dbprefix' => '',
    'pconnect' => FALSE,
    'db_debug' => TRUE,
    'cache_on' => FALSE,
    'cachedir' => '',
    'char_set' => 'utf8',
    'dbcollat' => 'utf8_general_ci',
    'swap_pre' => '',
    'encrypt' => FALSE,
    'compress' => FALSE,
    'stricton' => FALSE,
    'failover' => array(),
    'save_queries' => TRUE
);

// Accessing config
$dbConfig = $this->config->item('database');
$baseUrl = $this->config->site_url();

// config/app.php
$config['base_url'] = 'http://localhost:8080/';
$config['index_page'] = 'index.php';
$config['encryption_key'] = 'my_secret_key';
$config['sess_driver'] = 'database';
$config['sess_save_path'] = 'ci_sessions';
```

**Modern Symfony Pattern:**
```php
# .env
DATABASE_URL="mysql://root:@127.0.0.1:3306/ci_app?serverVersion=8.0"
APP_ENV=dev
APP_SECRET=your-secret-key-here

# config/packages/doctrine.yaml
doctrine:
    dbal:
        url: '%env(DATABASE_URL)%'
        options:
            charset: utf8mb4

# config/packages/session.yaml
framework:
    session:
        handler_id: session.handler.native_file
        save_path: '%kernel.project_dir%/var/sessions'

# config/services.yaml
parameters:
    app:
        base_url: '%env(BASE_URL)%'
        encryption_key: '%env(APP_SECRET)%'

services:
    _defaults:
        bind:
            string $baseUrl: '%app.base_url%'

    App\Application\Config\ConfigService:
        arguments:
            $baseUrl: '%app.base_url%'
            $encryptionKey: '%app.encryption_key%'

// Configuration Service
class ConfigService
{
    public function __construct(
        #[Autowire('%app.base_url%')]
        private string $baseUrl,

        #[Autowire('%app.encryption_key%')]
        private string $encryptionKey
    ) {}

    public function getBaseUrl(): string
    {
        return $this->baseUrl;
    }

    public function getEncryptionKey(): string
    {
        return $this->encryptionKey;
    }
}
```

---

## Summary Table

| CodeIgniter Pattern | Symfony Hexagonal Equivalent |
|---------------------|------------------------------|
| `$this->db->query()` | Doctrine DBAL + Repository |
| `$this->db->get()` | Doctrine QueryBuilder |
| `$this->load->model()` | Dependency Injection |
| `$this->session->userdata()` | Symfony SessionInterface |
| `$this->session->set_flashdata()` | Flash messages |
| `redirect()` | Symfony RedirectResponse |
| `site_url()` / `base_url()` | Router + Twig functions |
| `form_open()` | Symfony Form Component |
| `url_title()` | Str::slug() |
| `character_limiter()` | Str::limit() |
| `timespan()` | DateTime formatting |
| `$this->security->xss_clean()` | Symfony Validator + htmlspecialchars |
| `config->item()` | ParameterBag + .env |
| `database.php` config | doctrine.yaml |
| CI_Controller | AbstractController |

---

## Anti-Patterns to Avoid

1. **Global `$this` Reference** — Use dependency injection everywhere
2. **Model as God Object** — Split into Repository + Service layers
3. **Session as Data Store** — Use proper entities + Doctrine
4. **Helper Functions** — Replace with typed Services
5. **Direct DB Queries in Controllers** — Move to Application Services
6. **Active Record in Models** — Use Doctrine ORM
7. **Flash Data for Business Logic** — Use proper error handling
8. **Hardcoded Config** — Use environment variables + ParameterBag
