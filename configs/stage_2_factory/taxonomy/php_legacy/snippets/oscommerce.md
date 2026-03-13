# osCommerce Anti-Patterns Mapping

This document provides specific modernization patterns for osCommerce legacy PHP applications, mapping common osCommerce patterns to their Symfony hexagonal architecture equivalents.

## Database Access Patterns

### `tep_db_query()` → Doctrine Repository/QueryBuilder

**Legacy Pattern:**
```php
$query = tep_db_query("SELECT * FROM products WHERE products_id = '" . (int)$products_id . "'");
$product = tep_db_fetch_array($query);
```

**Modern Symfony Pattern:**
```php
// Repository (Driven Port Implementation)
class ProductRepository implements ProductRepositoryInterface
{
    public function __construct(
        private EntityManagerInterface $em
    ) {}

    public function findById(int $id): ?Product
    {
        return $this->em->find(Product::class, $id);
    }

    public function findByIdWithRelations(int $id): ?Product
    {
        return $this->em->createQueryBuilder()
            ->select('p', 'pd', 'i')
            ->from(Product::class, 'p')
            ->leftJoin('p.descriptions', 'pd')
            ->leftJoin('p.images', 'i')
            ->where('p.id = :id')
            ->setParameter('id', $id)
            ->getQuery()
            ->getOneOrNullResult();
    }
}

// Use Case / Application Service
class GetProductDetailsHandler
{
    public function __construct(
        private ProductRepositoryInterface $repository
    ) {}

    public function handle(GetProductDetailsQuery $query): ProductDTO
    {
        $product = $this->repository->findByIdWithRelations($query->productId);

        if ($product === null) {
            throw new ProductNotFoundException($query->productId);
        }

        return ProductDTO::fromEntity($product);
    }
}
```

---

### `tep_db_perform()` → Doctrine EntityManager

**Legacy Pattern:**
```php
$sql_data_array = [
    'products_name' => tep_db_prepare_input($_POST['products_name']),
    'products_price' => tep_db_prepare_input($_POST['products_price'])
];
tep_db_perform('products', $sql_data_array, 'update', "products_id = '" . (int)$id . "'");
```

**Modern Symfony Pattern:**
```php
class ProductService
{
    public function __construct(
        private EntityManagerInterface $em,
        private ProductRepositoryInterface $repository
    ) {}

    public function updateProduct(int $id, UpdateProductCommand $command): void
    {
        $product = $this->repository->findById($id);

        if (!$product) {
            throw new ProductNotFoundException($id);
        }

        $product->updateName($command->name);
        $product->updatePrice(Money::fromFloat($command->price));

        $this->em->flush();
    }
}
```

---

## Session & State Management

### `global $customer_id` → `UserInterface` / `TokenStorage`

**Legacy Pattern:**
```php
global $customer_id;

if (isset($customer_id)) {
    $customer_query = tep_db_query("SELECT * FROM customers WHERE customers_id = '" . (int)$customer_id . "'");
    $customer = tep_db_fetch_array($customer_query);
}
```

**Modern Symfony Pattern:**
```php
// Security Controller
class AccountController extends AbstractController
{
    #[Route('/account', name: 'account')]
    public function account(Request $request): Response
    {
        $user = $this->getUser(); // Returns UserInterface

        if (!$user instanceof CustomerUser) {
            throw $this->createAccessDeniedException();
        }

        return $this->render('account/index.html.twig', [
            'customer' => CustomerDTO::fromEntity($user->getCustomer())
        ]);
    }
}

// Domain Service for Customer Context
class CustomerContextService
{
    public function __construct(
        private TokenStorageInterface $tokenStorage,
        private CustomerRepositoryInterface $customerRepository
    ) {}

    public function getCurrentCustomer(): ?Customer
    {
        $token = $this->tokenStorage->getToken();

        if ($token === null || !$token->getUser() instanceof CustomerUser) {
            return null;
        }

        $customerId = $token->getUser()->getCustomerId();
        return $this->customerRepository->findById($customerId);
    }
}
```

---

### `$_SESSION['cart']` → `CartService` (Dependency Injection)

**Legacy Pattern:**
```php
global $cart;

if (!isset($_SESSION['cart'])) {
    $_SESSION['cart'] = new shoppingCart();
}

$_SESSION['cart']->add_cart($products_id, $quantity);
```

**Modern Symfony Pattern:**
```php
// Cart Service (Application Layer)
class CartService
{
    public function __construct(
        private SessionInterface $session,
        private ProductRepositoryInterface $productRepository,
        private CartSerializerInterface $serializer
    ) {}

    public function getCart(): Cart
    {
        $cartData = $this->session->get('cart', []);

        return $this->serializer->deserialize($cartData);
    }

    public function addToCart(int $productId, int $quantity): Cart
    {
        $product = $this->productRepository->findById($productId);

        if ($product === null) {
            throw new ProductNotFoundException($productId);
        }

        $cart = $this->getCart();
        $cart->addItem($product, $quantity);

        $this->saveCart($cart);

        return $cart;
    }

    private function saveCart(Cart $cart): void
    {
        $this->session->set('cart', $this->serializer->serialize($cart));
    }
}
```

---

### `tep_session_register()` → Symfony Session

**Legacy Pattern:**
```php
tep_session_register('customer_id');
tep_session_register('customer_default_address_id');
tep_session_register('customer_first_name');
```

**Modern Symfony Pattern:**
```php
// Session configuration (config/packages/framework.yaml)
// framework:
//     session:
//         handler_id: Symfony\Component\HttpFoundation\Session\Storage\Handler\PdoSessionHandler

// Using Session in Services
class OrderCreationService
{
    public function __construct(
        private SessionInterface $session,
        private CartService $cartService,
        private OrderRepositoryInterface $orderRepository
    ) {}

    public function createOrderFromCart(): Order
    {
        $cart = $this->cartService->getCart();

        $order = new Order(
            customerId: $this->session->get('customer_id'),
            items: $cart->getItems(),
            shippingAddress: $this->session->get('shipping_address')
        );

        $this->orderRepository->save($order);

        // Clear cart after order
        $this->session->remove('cart');

        return $order;
    }
}
```

---

## Configuration Constants

### `define(DIR_WS_*)` → `.env` parameters

**Legacy Pattern:**
```php
define('DIR_WS_IMAGES', 'images/');
define('DIR_WS_INCLUDES', 'includes/');
define('DIR_FS_CATALOG', '/var/www/html/');
define('DIR_FS_DOWNLOAD', DIR_FS_CATALOG . 'download/');
```

**Modern Symfony Pattern:**
```php
# .env
CATALOG_IMAGES_DIR=%kernel.project_dir%/public/images
CATALOG_DOWNLOAD_DIR=%kernel.project_dir%/var/downloads
CATALOG_INCLUDES_DIR=%kernel.project_dir%/includes

# config/packages/parameters.yaml
parameters:
    catalog.images_dir: '%env(CATALOG_IMAGES_DIR)%'
    catalog.download_dir: '%env(CATALOG_DOWNLOAD_DIR)%'
    catalog.includes_dir: '%env(CATALOG_INCLUDES_DIR)%'

// Service usage
class ImageService
{
    public function __construct(
        #[Autowire('%catalog.images_dir%')]
        private string $imagesDir
    ) {}

    public function getImagePath(string $filename): string
    {
        return $this->imagesDir . '/' . $filename;
    }
}
```

---

### `TABLE_*` constants → Doctrine Table Name Mapping

**Legacy Pattern:**
```php
define('TABLE_PRODUCTS', 'products');
define('TABLE_PRODUCTS_DESCRIPTION', 'products_description');

$query = tep_db_query("SELECT * FROM " . TABLE_PRODUCTS . " p LEFT JOIN " . TABLE_PRODUCTS_DESCRIPTION . " pd ON p.products_id = pd.products_id");
```

**Modern Symfony Pattern:**
```php
// Entity with Table mapping
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

    #[ORM\OneToMany(mappedBy: 'product', targetEntity: ProductDescription::class)]
    private Collection $descriptions;
}

// Repository
class ProductRepository extends ServiceEntityRepository implements ProductRepositoryInterface
{
    public function __construct(RegistryInterface $registry)
    {
        parent::__construct($registry, Product::class);
    }

    public function findAllWithDescriptions(): array
    {
        return $this->createQueryBuilder('p')
            ->leftJoin('p.descriptions', 'pd')
            ->addSelect('pd')
            ->getQuery()
            ->getResult();
    }
}
```

---

## URL & Navigation

### `tep_href_link()` → Symfony Router

**Legacy Pattern:**
```php
$link = tep_href_link('product_info.php', 'products_id=' . $product->products_id);
echo '<a href="' . $link . '">' . $product->products_name . '</a>';
```

**Modern Symfony Pattern:**
```php
// Twig template
<a href="{{ path('product_show', {id: product.id}) }}">{{ product.name }}</a>

// Or in PHP code
class ProductLinkGenerator
{
    public function __construct(
        private RouterInterface $router
    ) {}

    public function generateProductUrl(Product $product): string
    {
        return $this->router->generate('product_show', [
            'id' => $product->getId()
        ]);
    }
}
```

---

### `tep_redirect()` → Symfony RedirectResponse

**Legacy Pattern:**
```php
tep_redirect(tep_href_link('checkout_success.php', '', 'SSL'));

if ($messageStack->size('cart') > 0) {
    tep_redirect(tep_href_link('shopping_cart.php'));
}
```

**Modern Symfony Pattern:**
```php
class CheckoutController extends AbstractController
{
    #[Route('/checkout/success', name: 'checkout_success')]
    public function success(Request $request): Response
    {
        // ... processing

        return $this->redirectToRoute('checkout_success');
    }

    #[Route('/checkout/process', name: 'checkout_process')]
    public function process(Request $request): Response
    {
        if ($this->cartService->isEmpty()) {
            $this->addFlash('warning', 'Your cart is empty');

            return $this->redirectToRoute('cart_show');
        }

        // ... continue checkout
    }
}
```

---

## Template Rendering

### `tep_template_image_button()` → Twig + Asset Management

**Legacy Pattern:**
```php
echo tep_image_button('submit.gif', 'Continue');
echo tep_image(DIR_WS_IMAGES . $product->products_image, $product->products_name);
```

**Modern Symfony Pattern:**
```html+twig
{# Template #}
<img src="{{ asset('images/' ~ product.image, 'catalog') }}" alt="{{ product.name }}">

<button type="submit" class="btn btn-primary">
    Continue
</button>

{# Or use Symfony UX for interactive components #}
{{ ux_icon('mdi:cart') }}
```

---

## Error Handling

### `$messageStack->add()` → Symfony Flash Messages

**Legacy Pattern:**
```php
global $messageStack;

if ($error) {
    $messageStack->add('Error: Product not found', 'error');
} else {
    $messageStack->add('Success: Product updated', 'success');
}
```

**Modern Symfony Pattern:**
```php
class ProductUpdateController extends AbstractController
{
    public function update(Request $request, int $id): Response
    {
        try {
            $this->productService->update($id, $request->request->all());
            $this->addFlash('success', 'Success: Product updated');
        } catch (ProductNotFoundException $e) {
            $this->addFlash('error', 'Error: Product not found');
        }

        return $this->redirectToRoute('product_list');
    }
}
```

---

## Summary Table

| osCommerce Pattern | Symfony Hexagonal Equivalent |
|-------------------|------------------------------|
| `tep_db_query()` | `EntityManagerInterface` / Repository |
| `tep_db_perform()` | Doctrine `persist()` + `flush()` |
| `global $customer_id` | `TokenStorageInterface` + `UserInterface` |
| `$_SESSION['cart']` | `SessionInterface` + `CartService` |
| `tep_session_register()` | `SessionInterface::set()` |
| `define(DIR_WS_*)` | `.env` + parameters.yaml |
| `TABLE_*` | Doctrine Entity `@Table` |
| `tep_href_link()` | `RouterInterface::generate()` |
| `tep_redirect()` | `RedirectResponse` / `redirectToRoute()` |
| `tep_image_button()` | Twig + Asset component |
| `$messageStack->add()` | `FlashBagInterface` |

---

## Anti-Patterns to Avoid

1. **Entity Manager in Controllers** — Inject repositories instead
2. **Direct `tep_db_*` calls in Controllers** — Use Application Services
3. **Global Variables** — Inject everything via constructor
4. **Raw SQL Strings** — Use Doctrine QueryBuilder/DQL
5. **Session Access in Domain** — Pass session data as DTOs
6. **Constants in Business Logic** — Use configuration injection
