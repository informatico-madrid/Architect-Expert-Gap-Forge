# PrestaShop Anti-Patterns Mapping

This document provides specific modernization patterns for PrestaShop legacy PHP applications, mapping common PrestaShop patterns to their Symfony hexagonal architecture equivalents.

## Database Access Patterns

### `Db::getInstance()->execute()` → Doctrine DBAL

**Legacy Pattern:**
```php
// Direct SQL execution
$sql = "SELECT * FROM " . _DB_PREFIX_ . "product WHERE active = 1";
$result = Db::getInstance()->execute($sql);

// Execute with result
$sql = "SELECT id_product, name FROM " . _DB_PREFIX_ . "product_lang WHERE id_lang = " . (int)$id_lang;
$products = Db::getInstance()->executeS($sql);

// Execute with row
$sql = "SELECT COUNT(*) as total FROM " . _DB_PREFIX_ . "category";
$row = Db::getInstance()->getRow($sql);

// Execute with value
$count = Db::getInstance()->getValue("SELECT COUNT(*) FROM " . _DB_PREFIX_ . "orders");

// Insert/Update
Db::getInstance()->execute("INSERT INTO " . _DB_PREFIX_ . "product (id_product, name) VALUES (" . (int)$id . ", '" . pSQL($name) . "')");
Db::getInstance()->update(_DB_PREFIX_ . "product", ['active' => 1], "id_product = " . (int)$id);
```

**Modern Symfony Pattern:**
```php
// Repository (Driven Port Implementation)
class ProductRepository implements ProductRepositoryInterface
{
    public function __construct(
        private EntityManagerInterface $em
    ) {}

    public function findActive(): array
    {
        return $this->em->createQueryBuilder()
            ->select('p')
            ->from(Product::class, 'p')
            ->where('p.active = :active')
            ->setParameter('active', true)
            ->getQuery()
            ->getResult();
    }

    public function findByLanguage(int $languageId): array
    {
        return $this->em->createQueryBuilder()
            ->select('p.id', 'pl.name')
            ->from(Product::class, 'p')
            ->join(ProductLang::class, 'pl', 'WITH', 'p.id = pl.product')
            ->where('pl.language = :languageId')
            ->setParameter('languageId', $languageId)
            ->getQuery()
            ->getResult();
    }

    public function countAll(): int
    {
        return $this->em->createQueryBuilder()
            ->select('COUNT(o)')
            ->from(Order::class, 'o')
            ->getQuery()
            ->getSingleScalarResult();
    }

    public function findProductById(int $id): ?Product
    {
        return $this->em->find(Product::class, $id);
    }

    public function createProduct(string $name): Product
    {
        $product = new Product();
        $product->setName($name);

        $this->em->persist($product);
        $this->em->flush();

        return $product;
    }

    public function activateProduct(int $id): void
    {
        $product = $this->em->find(Product::class, $id);

        if ($product === null) {
            throw new ProductNotFoundException($id);
        }

        $product->setActive(true);
        $this->em->flush();
    }
}

// Use Case / Application Service
class ProductManagementService
{
    public function __construct(
        private ProductRepositoryInterface $repository
    ) {}

    public function getActiveProducts(): array
    {
        return $this->repository->findActive();
    }

    public function getProductsByLanguage(int $languageId): array
    {
        return $this->repository->findByLanguage($languageId);
    }

    public function activateProduct(int $productId): void
    {
        $this->repository->activateProduct($productId);
    }
}
```

---

### `Db::getInstance()->insert` / `Db::getInstance()->update` → Doctrine ORM

**Legacy Pattern:**
```php
// Insert
Db::getInstance()->insert('product', [
    'id_product' => (int)$id_product,
    'name' => pSQL($name),
    'price' => (float)$price,
    'active' => 1,
    'date_add' => date('Y-m-d H:i:s')
]);

// Update
Db::getInstance()->update(
    'product',
    ['price' => (float)$new_price, 'active' => (int)$active],
    'id_product = ' . (int)$id_product
);

// Delete
Db::getInstance()->delete('product', 'id_product = ' . (int)$id_product);
```

**Modern Symfony Pattern:**
```php
class ProductRepository extends ServiceEntityRepository implements ProductRepositoryInterface
{
    public function __construct(RegistryInterface $registry)
    {
        parent::__construct($registry, Product::class);
    }

    public function save(Product $product): void
    {
        $this->getEntityManager()->persist($product);
        $this->getEntityManager()->flush();
    }

    public function delete(int $productId): void
    {
        $product = $this->find($productId);

        if ($product !== null) {
            $this->getEntityManager()->remove($product);
            $this->getEntityManager()->flush();
        }
    }

    public function updatePrice(int $productId, float $price): void
    {
        $this->createQueryBuilder('p')
            ->update(Product::class, 'p')
            ->set('p.price', ':price')
            ->where('p.id = :id')
            ->setParameter('price', $price)
            ->setParameter('id', $productId)
            ->getQuery()
            ->execute();
    }
}
```

---

## Context & Current User

### `Context::getContext()->customer` → DI UserInterface

**Legacy Pattern:**
```php
// Get current customer
$context = Context::getContext();
$customer = $context->customer;

// Check if logged in
if (Validate::isLoadedObject($context->customer) && $context->customer->isLogged()) {
    $customer_id = $context->customer->id;
    $email = $context->customer->email;
    $firstname = $context->customer->firstname;
}

// Access cart
$cart = $context->cart;
$cart_id = $context->cart->id;

// Access language
$language = $context->language;
$lang_id = $context->language->id;

// Access shop
$shop = $context->shop;
```

**Modern Symfony Pattern:**
```php
// Current User Injection (replaces Context::getContext()->customer)
class ProductController extends AbstractController
{
    public function __construct(
        private ProductRepositoryInterface $productRepository,
        private CustomerRepositoryInterface $customerRepository
    ) {}

    #[Route('/products', name: 'product_list')]
    public function listProducts(): Response
    {
        // Get current authenticated customer via TokenStorage
        $customer = $this->getUser(); // Returns Customer entity implementing UserInterface

        if ($customer !== null) {
            $customerId = $customer->getId();
            $customerEmail = $customer->getEmail();
            $customerFirstName = $customer->getFirstName();
        }

        $products = $this->productRepository->findActive();

        return $this->render('product/list.html.twig', [
            'products' => $products,
            'customer' => $customer
        ]);
    }
}

// Service that needs customer context
class WishlistService
{
    public function __construct(
        private TokenStorageInterface $tokenStorage,
        private WishlistRepositoryInterface $wishlistRepository
    ) {}

    public function getCustomerWishlist(): ?Wishlist
    {
        $user = $this->tokenStorage->getToken()?->getUser();

        if (!$user instanceof Customer) {
            return null;
        }

        return $this->wishlistRepository->findByCustomer($user->getId());
    }
}

// Cart Service (replaces Context::getContext()->cart)
class CartService
{
    public function __construct(
        private CartRepositoryInterface $cartRepository,
        private TokenStorageInterface $tokenStorage
    ) {}

    public function getCurrentCart(): ?Cart
    {
        $user = $this->tokenStorage->getToken()?->getUser();

        if (!$user instanceof Customer) {
            return null;
        }

        return $this->cartRepository->findActiveCartByCustomer($user->getId());
    }
}
```

---

## Input Handling

### `Tools::getValue()` → Symfony Request with Validation

**Legacy Pattern:**
```php
// Get values from GET/POST
$id_product = Tools::getValue('id_product');
$name = Tools::getValue('name');
$price = Tools::getValue('price');
$action = Tools::getValue('action');

// With default value
$limit = Tools::getValue('limit', 10);

// Boolean conversion
$active = Tools::getValue('active', false);

// JSON input
$data = Tools::jsonDecode(Tools::getValue('data'));

// File upload
$file = Tools::fileAttachment('attachment');

// URL parameters
$back = Tools::getValue('back');

// Sanitization
$safe_name = Tools::safeFilename(Tools::getValue('filename'));
$html_content = Tools::htmlentitiesUTF8(Tools::getValue('content'));
```

**Modern Symfony Pattern:**
```php
// Form Type with Validation (replaces Tools::getValue)
class ProductFilterType extends AbstractType
{
    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        $builder
            ->add('id_product', IntegerType::class, [
                'required' => false,
                'constraints' => [
                    new Positive()
                ]
            ])
            ->add('name', TextType::class, [
                'required' => false,
                'constraints' => [
                    new Length(['max' => 255])
                ]
            ])
            ->add('price', MoneyType::class, [
                'required' => false,
                'constraints' => [
                    new PositiveOrZero()
                ]
            ])
            ->add('active', CheckboxType::class, [
                'required' => false
            ])
            ->add('limit', IntegerType::class, [
                'required' => false,
                'data' => 10,
                'constraints' => [
                    new Range(['min' => 1, 'max' => 100])
                ]
            ]);
    }

    public function configureOptions(OptionsResolver $resolver): void
    {
        $resolver->setDefaults([
            'data_class' => ProductFilter::class,
            'method' => 'GET',
            'csrf_protection' => false // For API endpoints
        ]);
    }
}

// DTO for the filter
class ProductFilter
{
    private ?int $idProduct = null;
    private ?string $name = null;
    private ?float $price = null;
    private ?bool $active = null;
    private int $limit = 10;

    // Getters and setters
}

// Controller using the form
class ProductController extends AbstractController
{
    public function __construct(
        private ProductRepositoryInterface $productRepository
    ) {}

    #[Route('/products', name: 'product_list')]
    public function list(Request $request): Response
    {
        $filter = new ProductFilter();

        $form = $this->createForm(ProductFilterType::class, $filter);
        $form->handleRequest($request);

        if ($form->isSubmitted() && $form->isValid()) {
            $filter = $form->getData();
            $products = $this->productRepository->findByFilter($filter);
        } else {
            $products = $this->productRepository->findAll();
        }

        return $this->render('product/list.html.twig', [
            'products' => $products,
            'form' => $form->createView()
        ]);
    }
}

// For JSON APIs
#[RestController]
class ApiProductController extends AbstractController
{
    public function __construct(
        private ProductRepositoryInterface $productRepository
    ) {}

    #[Route('/api/products', name: 'api_product_list', methods: ['POST'])]
    public function createFromJson(Request $request): JsonResponse
    {
        $data = json_decode($request->getContent(), true);

        $violations = $this->validator->validate($data);

        if (count($violations) > 0) {
            return $this->json([
                'errors' => (string) $violations
            ], 400);
        }

        // Process validated data
        $product = new Product();
        $product->setName($data['name']);
        // ...

        return $this->json($product, 201);
    }
}
```

---

## Configuration

### `Configuration::get()` → Symfony ParameterBag

**Legacy Pattern:**
```php
// Get configuration values
$shop_name = Configuration::get('PS_SHOP_NAME');
$shop_email = Configuration::get('PS_SHOP_EMAIL');
$theme = Configuration::get('PS_THEME');
$products_per_page = Configuration::get('PS_PRODUCTS_PER_PAGE');

// With language
$welcome_message = Configuration::get('PS_WELCOME_MESSAGE', $id_lang);

// With default
$limit = Configuration::get('PS_PRODUCTS_PER_PAGE', $id_lang, $id_shop, 12);

// Get multiple
$configs = Configuration::getMultiple([
    'PS_SHOP_NAME',
    'PS_SHOP_EMAIL',
    'PS_LANG_DEFAULT'
]);

// Set configuration
Configuration::updateValue('PS_CUSTOM_THEME', $value);
Configuration::updateValue('PS_PRODUCTS_PER_PAGE', 24, false, $id_shop);
```

**Modern Symfony Pattern:**
```yaml
# config/packages/parameters.yaml
parameters:
    shop.name: '%env(SHOP_NAME)%'
    shop.email: '%env(SHOP_EMAIL)%'
    shop.theme: 'classic'
    products.per_page: 12
```

```php
class SettingsService
{
    public function __construct(
        #[Autowire('%shop.name%')]
        private string $shopName,

        #[Autowire('%shop.email%')]
        private string $shopEmail,

        #[Autowire('%shop.theme%')]
        private string $theme,

        #[Autowire('%products.per_page%')]
        private int $productsPerPage,

        private ParameterBagInterface $params
    ) {}

    public function getShopName(): string
    {
        return $this->shopName;
    }

    public function getShopEmail(): string
    {
        return $this->shopEmail;
    }

    public function getProductsPerPage(): int
    {
        return $this->productsPerPage;
    }

    public function get(string $key, mixed $default = null): mixed
    {
        return $this->params->get($key, $default);
    }
}
```

---

## Hook System

### `Hook::exec()` → Symfony EventDispatcher

**Legacy Pattern:**
```php
// Execute hook
Hook::exec('actionProductSave', ['id_product' => $id_product, 'product' => $product]);

// Execute with return value
$html = Hook::exec('displayHeader');

// Execute with multiple parameters
Hook::exec('actionCustomerLogin', [
    'customer' => $customer
]);

// Register hook
Hook::register('actionProductSave', $module->name, 'hookProductSave');

// Legacy hook action
public function hookDisplayHeader($params)
{
    return '<link rel="stylesheet" href="...">';
}
```

**Modern Symfony Pattern:**
```php
// Event Definition
class ProductSavedEvent extends Event
{
    public const NAME = 'product.saved';

    public function __construct(
        private Product $product,
        private bool $isNew
    ) {}

    public function getProduct(): Product
    {
        return $this->product;
    }

    public function isNew(): bool
    {
        return $this->isNew;
    }
}

class CustomerLoginEvent extends Event
{
    public const NAME = 'customer.login';

    public function __construct(
        private Customer $customer
    ) {}

    public function getCustomer(): Customer
    {
        return $this->customer;
    }
}

// Event Listener
class ProductSaveListener
{
    public function __construct(
        private ProductSearchIndexService $indexService
    ) {}

    #[AsEventListener(event: ProductSavedEvent::NAME)]
    public function onProductSave(ProductSavedEvent $event): void
    {
        $product = $event->getProduct();

        if (!$event->isNew()) {
            $this->indexService->updateIndex($product->getId());
        }
    }
}

// Dispatching Events
class ProductController extends AbstractController
{
    public function __construct(
        private EventDispatcherInterface $eventDispatcher,
        private ProductRepositoryInterface $productRepository
    ) {}

    #[Route('/product/{id}', name: 'product_save')]
    public function save(Request $request, int $id = null): Response
    {
        $product = $id ? $this->productRepository->find($id) : new Product();

        $form = $this->createForm(ProductType::class, $product);
        $form->handleRequest($request);

        if ($form->isSubmitted() && $form->isValid()) {
            $isNew = $id === null;
            $this->productRepository->save($product);

            $this->eventDispatcher->dispatch(new ProductSavedEvent($product, $isNew));

            return $this->redirectToRoute('product_show', ['id' => $product->getId()]);
        }

        return $this->render('product/form.html.twig', [
            'form' => $form->createView()
        ]);
    }
}
```

---

## Smarty Templates

### Smarty → Twig Templates

**Legacy Pattern:**
```smarty
{* Product listing *}
{foreach from=$products item=product}
    <div class="product">
        <h2>{$product.name}</h2>
        <p class="price">{convertPrice price=$product.price}</p>
        <a href="{$link->getProductLink($product.id_product)}">View</a>
    </div>
{/foreach}

{* Smarty variables *}
{$shop_name}
{$language.iso_code}
{$cart->getTotal()}

{* Smarty modifiers *}
{$product.description|escape:'html':'UTF-8'|nl2br}
{$product.price|number_format:2:',':' '}

{* Smarty conditionals *}
{if $product.quantity > 0}
    <span class="in-stock">In Stock</span>
{else}
    <span class="out-of-stock">Out of Stock</span>
{/if}
```

**Modern Symfony Pattern:**
```twig
{# Product listing #}
{% for product in products %}
    <div class="product">
        <h2>{{ product.name }}</h2>
        <p class="price">{{ product.price|format_price('EUR') }}</p>
        <a href="{{ path('product_show', {id: product.id}) }}">View</a>
    </div>
{% endfor %}

{# Twig variables #}
{{ shop_name }}
{{ language.isoCode }}
{{ cart.total }}

{# Twig filters #}
{{ product.description|escape('html')|nl2br }}
{{ product.price|format_number({fraction_digit: 2}) }}

{# Twig conditionals #}
{% if product.quantity > 0 %}
    <span class="in-stock">In Stock</span>
{% else %}
    <span class="out-of-stock">Out of Stock</span>
{% endif %}
```

```php
// Controller (replaces $link->getProductLink)
class ProductController extends AbstractController
{
    #[Route('/product/{id}/{slug}', name: 'product_show')]
    public function show(int $id): Response
    {
        $product = $this->productRepository->find($id);

        return $this->render('product/show.html.twig', [
            'product' => $product,
            'shop_name' => $this->settingsService->getShopName(),
            'cart' => $this->cartService->getCurrentCart()
        ]);
    }
}
```

---

## Module Management

### `Module::getInstanceByName()` → DI Container

**Legacy Pattern:**
```php
// Get module instance
$module = Module::getInstanceByName('paypal');

if (Validate::isLoadedObject($module)) {
    $module->hookPayment($params);
}

// Get module configuration
$config = Module::getInstanceByName('statsproduct')->getConfigFieldsValues();

// Check if module installed
if (Module::isInstalled('mailalerts')) {
    // ...
}
```

**Modern Symfony Pattern:**
```php
// Service Definition (replaces Module::getInstanceByName)
# config/services.yaml
services:
    App\Payment\PayPalService:
        autowire: true
        tags: ['payment.gateway']

    App\Payment\PaymentGatewayInterface:
        class: App\Payment\PayPalService
        autowire: true
        tags: ['payment.gateway']

// Using the service
class OrderController extends AbstractController
{
    public function __construct(
        private PaymentGatewayInterface $paymentGateway,
        private iterable $paymentGateways // All services tagged with payment.gateway
    ) {}

    public function processPayment(Request $request): Response
    {
        // Use injected service directly
        $result = $this->paymentGateway->process($amount);

        // Or iterate through all registered gateways
        foreach ($this->paymentGateways as $gateway) {
            // ...
        }
    }
}

// Module configuration as service parameters
class StatsProductService
{
    public function __construct(
        #[Autowire('%stats_product.enabled%')]
        private bool $enabled,

        #[Autowire('%stats_product.update_interval%')]
        private int $updateInterval
    ) {}
}
```

---

## Validation

### `Validate::is*()` → Symfony Form Validation

**Legacy Pattern:**
```php
// Email validation
if (!Validate::isEmail($email)) {
    $errors[] = 'Invalid email';
}

// Generic string validation
if (!Validate::isName($name)) {
    $errors[] = 'Invalid name';
}

if (!Validate::isPhoneNumber($phone)) {
    $errors[] = 'Invalid phone';
}

// Number validation
if (!Validate::isInt($id)) {
    $errors[] = 'Invalid ID';
}

if (!Validate::isPrice($price)) {
    $errors[] = 'Invalid price';
}

// Date validation
if (!Validate::isDate($date)) {
    $errors[] = 'Invalid date';
}

// Object validation
if (!Validate::isLoadedObject($customer)) {
    $errors[] = 'Customer not loaded';
}

// Length validation
if (!Validate::isLength($name, 3, 128)) {
    $errors[] = 'Name must be between 3 and 128 characters';
}
```

**Modern Symfony Pattern:**
```php
// Validation Constraints (replaces Validate::is*)
use Symfony\Component\Validator\Constraints as Assert;

class CustomerRegistrationType extends AbstractType
{
    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        $builder
            ->add('email', Assert\Email::class, [
                'message' => 'The email "{{ value }}" is not a valid email.',
            ])
            ->add('firstName', [
                Assert\NotBlank(),
                Assert\Length(['min' => 3, 'max' => 128]),
            ])
            ->add('lastName', [
                Assert\NotBlank(),
                Assert\Length(['min' => 3, 'max' => 128]),
            ])
            ->add('phone', Assert\Regex::class, [
                'pattern' => '/^\+?[0-9\s\-()]+$/',
                'message' => 'Invalid phone number format',
            ])
            ->add('price', Assert\PositiveOrZero::class)
            ->add('birthDate', Assert\Date::class);
    }
}

// Standalone validation
class CustomerValidator
{
    public function __construct(
        private ValidatorInterface $validator
    ) {}

    public function validate(array $data): ValidationResult
    {
        $constraints = new Assert\Collection([
            'email' => new Assert\Email(),
            'name' => [
                new Assert\NotBlank(),
                new Assert\Length(['min' => 3, 'max' => 128]),
            ],
            'phone' => new Assert\Regex([
                'pattern' => '/^\+?[0-9\s\-()]+$/',
            ]),
        ]);

        $violations = $this->validator->validate($data, $constraints);

        return new ValidationResult($violations);
    }
}
```

---

## Summary Table

| PrestaShop Pattern | Symfony Hexagonal Equivalent |
|--------------------|------------------------------|
| `Db::getInstance()->execute()` | `EntityManagerInterface` / Repository |
| `Db::getInstance()->executeS()` | Doctrine QueryBuilder with `getResult()` |
| `Db::getInstance()->getValue()` | `getSingleScalarResult()` |
| `Context::getContext()->customer` | `TokenStorageInterface::getToken()->getUser()` |
| `Context::getContext()->cart` | `CartService` (DI) |
| `Tools::getValue()` | `Request` + Form Type with Validation |
| `Configuration::get()` | `ParameterBagInterface::get()` |
| `Hook::exec()` | `EventDispatcherInterface::dispatch()` |
| `Module::getInstanceByName()` | DI Container with autowiring |
| `Validate::isEmail()` | `Assert\Email` constraint |
| `Validate::is*()` | Symfony Validator constraints |
| Smarty templates | Twig templates |
| `$link->getProductLink()` | `Router::generate()` / `path()` |

---

## Anti-Patterns to Avoid

1. **Direct `Db::getInstance()` queries in Controllers** — Use repositories
2. **Global `Context::getContext()` calls** — Inject services via DI
3. **Raw `Tools::getValue()` without validation** — Use Symfony Forms
4. **PrestaShop hooks in domain logic** — Use Symfony EventDispatcher
5. **Global `Configuration::get()` throughout** — Use ParameterBag injection
6. **Smarty templates in src/** — Move to Twig templates in `templates/`
7. **`Module::getInstanceByName()` for services** — Use service autowiring
8. **Manual `Validate::is*()` checks** — Use Symfony Validator component
