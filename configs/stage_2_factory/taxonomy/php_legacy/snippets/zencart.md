# Zen Cart Anti-Patterns Mapping

This document provides specific modernization patterns for Zen Cart legacy PHP applications, mapping common Zen Cart patterns to their Symfony hexagonal architecture equivalents.

## Database Access Patterns

### `zen_db_perform()` → Doctrine ORM

**Legacy Pattern:**
```php
$sql_data_array = [
    'products_name' => zen_db_prepare_input($_POST['products_name']),
    'products_price' => zen_db_prepare_input($_POST['products_price']),
    'products_last_modified' => 'now()'
];
zen_db_perform(TABLE_PRODUCTS, $sql_data_array, 'update', "products_id = '" . (int)$products_id . "'");
```

**Modern Symfony Pattern:**
```php
// Entity (Domain Model)
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

    #[ORM\Column(type: 'decimal', precision: 15, scale: 2)]
    private float $price;

    #[ORM\Column(type: 'datetime')]
    private ?DateTimeInterface $lastModified = null;

    public function updateFromDTO(UpdateProductDTO $dto): void
    {
        $this->name = $dto->name;
        $this->price = $dto->price;
        $this->lastModified = new DateTimeImmutable();
    }
}

// Repository Interface (Driven Port)
interface ProductRepositoryInterface
{
    public function find(int $id): ?Product;
    public function save(Product $product): void;
    public function remove(Product $product): void;
}

// Repository Implementation (Driven Adapter)
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

    public function save(Product $product): void
    {
        $this->getEntityManager()->persist($product);
        $this->getEntityManager()->flush();
    }
}

// Application Service (Use Case)
class UpdateProductHandler
{
    public function __construct(
        private ProductRepositoryInterface $repository,
        private EntityManagerInterface $em
    ) {}

    public function handle(UpdateProductCommand $command): ProductDTO
    {
        $product = $this->repository->find($command->productId);

        if ($product === null) {
            throw new ProductNotFoundException($command->productId);
        }

        $product->updateFromDTO($command->dto);
        $this->em->flush();

        return ProductDTO::fromEntity($product);
    }
}
```

---

### `zen_db_query()` → Doctrine QueryBuilder

**Legacy Pattern:**
```php
$query = zen_db_query("
    SELECT p.*, pd.products_name, p.products_id
    FROM " . TABLE_PRODUCTS . " p
    LEFT JOIN " . TABLE_PRODUCTS_DESCRIPTION . " pd ON p.products_id = pd.products_id
    WHERE p.products_status = '1'
    AND pd.language_id = '" . (int)$_SESSION['languages_id'] . "'
    ORDER BY p.products_date_added DESC
");
while ($product = zen_db_fetch_array($query)) {
    // process product
}
```

**Modern Symfony Pattern:**
```php
// Repository with QueryBuilder
class ProductRepository extends ServiceEntityRepository implements ProductRepositoryInterface
{
    public function __construct(RegistryInterface $registry)
    {
        parent::__construct($registry, Product::class);
    }

    public function findActiveWithDescription(int $languageId): array
    {
        return $this->createQueryBuilder('p')
            ->innerJoin('p.descriptions', 'pd')
            ->andWhere('p.status = :status')
            ->andWhere('pd.language = :languageId')
            ->setParameter('status', true)
            ->setParameter('languageId', $languageId)
            ->orderBy('p.dateAdded', 'DESC')
            ->getQuery()
            ->getResult();
    }

    public function findLatestActive(int $languageId, int $limit = 10): array
    {
        return $this->createQueryBuilder('p')
            ->innerJoin('p.descriptions', 'pd')
            ->andWhere('p.status = :status')
            ->andWhere('pd.language = :languageId')
            ->setParameter('status', true)
            ->setParameter('languageId', $languageId)
            ->orderBy('p.dateAdded', 'DESC')
            ->setMaxResults($limit)
            ->getQuery()
            ->getResult();
    }
}
```

---

### `zen_db_prepare_input()` → Symfony Form Validation

**Legacy Pattern:**
```php
$product_name = zen_db_prepare_input($_POST['products_name']);
$product_description = zen_db_prepare_input($_POST['products_description']);
$product_price = zen_db_prepare_input($_POST['products_price']);
```

**Modern Symfony Pattern:**
```php
// Form Type with Validation
class ProductType extends AbstractType
{
    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        $builder
            ->add('name', TextType::class, [
                'required' => true,
                'constraints' => [
                    new NotBlank(['message' => 'Product name is required']),
                    new Length([
                        'max' => 255,
                        'maxMessage' => 'Product name cannot be longer than {{ limit }} characters'
                    ])
                ]
            ])
            ->add('description', TextareaType::class, [
                'required' => false,
                'constraints' => [
                    new Length([
                        'max' => 65535,
                        'maxMessage' => 'Description cannot be longer than {{ limit }} characters'
                    ])
                ]
            ])
            ->add('price', MoneyType::class, [
                'required' => true,
                'currency' => 'USD',
                'constraints' => [
                    new NotBlank(['message' => 'Price is required']),
                    new Positive(['message' => 'Price must be positive'])
                ]
            ]);
    }
}

// Controller usage
class ProductController extends AbstractController
{
    public function edit(Request $request, Product $product): Response
    {
        $form = $this->createForm(ProductType::class, $product);
        $form->handleRequest($request);

        if ($form->isSubmitted() && $form->isValid()) {
            $product = $form->getData();
            $this->productRepository->save($product);
            $this->addFlash('success', 'Product updated successfully');

            return $this->redirectToRoute('product_list');
        }

        return $this->render('product/edit.html.twig', [
            'form' => $form
        ]);
    }
}
```

---

## Session & Authentication

### `$_SESSION['customer_id']` → `Security::getUser()`

**Legacy Pattern:**
```php
if (isset($_SESSION['customer_id'])) {
    $customer_id = $_SESSION['customer_id'];
    $customer_query = zen_db_query("
        SELECT customers_id, customers_firstname, customers_lastname,
               customers_email_address, customers_default_address_id
        FROM " . TABLE_CUSTOMERS . "
        WHERE customers_id = '" . (int)$customer_id . "'
    ");
    $customer = zen_db_fetch_array($customer_query);
}
```

**Modern Symfony Pattern:**
```php
// Security Configuration (config/packages/security.yaml)
# security:
#     firewalls:
#         main:
#             pattern: ^/
#             form_login:
#                 provider: doctrine
#                 login_path: login
#                 check_path: login_check
#             logout:
#                 path: logout
#                 target: home
#     providers:
#         doctrine:
#             entity:
#                 class: App\Domain\Customer\Entity\CustomerUser
#                 property: email

// Entity implementing UserInterface
#[ORM\Entity]
#[ORM\Table(name: 'customers')]
class CustomerUser implements UserInterface, PasswordAuthenticatedUserInterface
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\Column(type: 'string', length: 255, unique: true)]
    private string $email;

    #[ORM\Column(type: 'string', length: 255)]
    private string $password;

    #[ORM\OneToOne(targetEntity: Customer::class, mappedBy: 'user')]
    private ?Customer $customer = null;

    public function getRoles(): array
    {
        return ['ROLE_CUSTOMER'];
    }

    public function getUserIdentifier(): string
    {
        return $this->email;
    }
}

// Controller with Security
class AccountController extends AbstractController
{
    #[Route('/account', name: 'account')]
    public function account(): Response
    {
        $user = $this->getUser();

        if (!$user instanceof CustomerUser) {
            return $this->redirectToRoute('login');
        }

        $customer = $user->getCustomer();

        return $this->render('account/index.html.twig', [
            'customer' => CustomerDTO::fromEntity($customer)
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

        if ($token === null) {
            return null;
        }

        $user = $token->getUser();

        if (!$user instanceof CustomerUser) {
            return null;
        }

        return $user->getCustomer();
    }
}
```

---

### `$_SESSION['cart']` → CartService with Session

**Legacy Pattern:**
```php
if (!isset($_SESSION['cart']) || !is_object($_SESSION['cart'])) {
    $_SESSION['cart'] = new shoppingCart();
}

$_SESSION['cart']->add_cart($products_id, $quantity, $attributes_id);
$cart_total = $_SESSION['cart']->show_total();
```

**Modern Symfony Pattern:**
```php
// Cart Entity (Domain Model)
class Cart
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\ManyToOne(targetEntity: Customer::class)]
    #[ORM\JoinColumn(name: 'customer_id', nullable: true)]
    private ?Customer $customer = null;

    #[ORM\OneToMany(mappedBy: 'cart', targetEntity: CartItem::class, cascade: ['persist', 'remove'])]
    private Collection $items;

    private array $sessionData = [];

    public function addItem(Product $product, int $quantity, array $attributes = []): void
    {
        foreach ($this->items as $item) {
            if ($item->getProduct()->getId() === $product->getId()) {
                $item->increaseQuantity($quantity);
                return;
            }
        }

        $item = new CartItem();
        $item->setProduct($product);
        $item->setQuantity($quantity);
        $item->setAttributes($attributes);
        $item->setCart($this);
        $this->items->add($item);
    }

    public function getTotal(): Money
    {
        $total = Money::USD(0);
        foreach ($this->items as $item) {
            $total = $total->add($item->getTotal());
        }
        return $total;
    }
}

// Cart Service (Application Layer)
class CartService
{
    public function __construct(
        private SessionInterface $session,
        private ProductRepositoryInterface $productRepository,
        private CartSerializerInterface $serializer,
        private EntityManagerInterface $em
    ) {}

    public function getCart(): Cart
    {
        $cartId = $this->session->get('cart_id');

        if ($cartId !== null) {
            $cart = $this->em->find(Cart::class, $cartId);
            if ($cart !== null) {
                return $cart;
            }
        }

        return new Cart();
    }

    public function addToCart(int $productId, int $quantity, array $attributes = []): Cart
    {
        $product = $this->productRepository->find($productId);

        if ($product === null) {
            throw new ProductNotFoundException($productId);
        }

        $cart = $this->getCart();
        $cart->addItem($product, $quantity, $attributes);

        $this->saveCart($cart);

        return $cart;
    }

    private function saveCart(Cart $cart): void
    {
        $this->em->persist($cart);
        $this->em->flush();
        $this->session->set('cart_id', $cart->getId());
    }
}
```

---

## Navigation & Redirection

### `zen_redirect()` → Symfony `RedirectResponse`

**Legacy Pattern:**
```php
zen_redirect(zen_href_link(FILENAME_DEFAULT, 'cPath=' . $cPath));

if ($messageStack->size('checkout') > 0) {
    zen_redirect(zen_href_link(FILENAME_CHECKOUT_SHIPPING, '', 'SSL'));
}

zen_redirect(zen_href_link(FILENAME_LOGIN, '', 'SSL'));
```

**Modern Symfony Pattern:**
```php
class CheckoutController extends AbstractController
{
    #[Route('/checkout/shipping', name: 'checkout_shipping')]
    public function shipping(Request $request): Response
    {
        $cart = $this->cartService->getCart();

        if ($cart->isEmpty()) {
            $this->addFlash('warning', 'Your cart is empty');

            return $this->redirectToRoute('cart_show');
        }

        if (!$this->getUser()) {
            $this->addFlash('notice', 'Please log in to continue checkout');

            return $this->redirectToRoute('login', [
                '_redirect' => $this->generateUrl('checkout_shipping')
            ]);
        }

        // ... continue checkout process
    }

    #[Route('/products/{categoryPath}', name: 'product_category')]
    public function category(string $categoryPath): Response
    {
        $category = $this->categoryRepository->findByPath($categoryPath);

        if ($category === null) {
            throw $this->createNotFoundException('Category not found');
        }

        return $this->render('product/category.html.twig', [
            'category' => $category
        ]);
    }
}

// With Response for special cases
class AuthController extends AbstractController
{
    #[Route('/login', name: 'login')]
    public function login(AuthenticationUtils $authenticationUtils): Response
    {
        $error = $authenticationUtils->getLastAuthenticationError();

        return $this->render('security/login.html.twig', [
            'last_username' => $authenticationUtils->getLastUsername(),
            'error' => $error
        ]);
    }

    #[Route('/logout', name: 'logout')]
    public function logout(): void
    {
        throw new \LogicException('This method should not be reached');
    }
}
```

---

### `zen_href_link()` → Symfony Router

**Legacy Pattern:**
```php
$product_link = zen_href_link(FILENAME_PRODUCT_INFO, 'products_id=' . $products_id);
$category_link = zen_href_link(FILENAME_DEFAULT, 'cPath=' . $cPath);
$image_link = zen_href_link(DIR_WS_IMAGES . $filename);
```

**Modern Symfony Pattern:**
```php
// In Twig templates
<a href="{{ path('product_info', {id: product.id}) }}">{{ product.name }}</a>
<a href="{{ path('product_category', {categoryPath: category.path}) }}">{{ category.name }}</a>
<img src="{{ asset('images/' ~ filename, 'catalog') }}">

// In PHP services
class ProductLinkGenerator
{
    public function __construct(
        private RouterInterface $router,
        private UrlGeneratorInterface $urlGenerator
    ) {}

    public function generateProductUrl(int $productId): string
    {
        return $this->router->generate('product_info', [
            'id' => $productId
        ]);
    }

    public function generateCategoryUrl(string $categoryPath): string
    {
        return $this->urlGenerator->generate('product_category', [
            'categoryPath' => $categoryPath
        ]);
    }

    public function generateImageUrl(string $filename): string
    {
        return $this->router->getContext()->getBaseUrl() . '/images/' . $filename;
    }
}
```

---

## Email

### `zen_mail()` → Symfony Mailer Component

**Legacy Pattern:**
```php
zen_mail(
    $customer_name,
    $customer_email_address,
    EMAIL_TEXT_SUBJECT,
    $email_text,
    STORE_OWNER,
    STORE_OWNER_EMAIL_ADDRESS,
    $html_msg,
    'direct'
);
```

**Modern Symfony Pattern:**
```php
// Email Template (templates/emails/order_confirmation.html.twig)
{# templates/emails/order_confirmation.html.twig #}
<!DOCTYPE html>
<html>
<body>
    <h1>Order Confirmation</h1>
    <p>Dear {{ customer.firstName }} {{ customer.lastName }},</p>
    <p>Thank you for your order! Here are your order details:</p>
    <table>
        <thead>
            <tr>
                <th>Product</th>
                <th>Quantity</th>
                <th>Price</th>
            </tr>
        </thead>
        <tbody>
            {% for item in order.items %}
            <tr>
                <td>{{ item.productName }}</td>
                <td>{{ item.quantity }}</td>
                <td>{{ item.price|format_currency('USD') }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    <p><strong>Total: {{ order.total|format_currency('USD') }}</strong></p>
</body>
</html>

// Email Service (Application Layer)
class EmailService
{
    public function __construct(
        private MailerInterface $mailer,
        private Environment $twig,
        private LoggerInterface $logger
    ) {}

    public function sendOrderConfirmation(Customer $customer, Order $order): void
    {
        try {
            $email = (new Email())
                ->from(new Address('noreply@example.com', 'Store Name'))
                ->to(new Address($customer->getEmail(), $customer->getFirstName()))
                ->subject('Order Confirmation - #' . $order->getId())
                ->html($this->twig->render('emails/order_confirmation.html.twig', [
                    'customer' => $customer,
                    'order' => $order
                ]))
                ->text($this->twig->render('emails/order_confirmation.txt.twig', [
                    'customer' => $customer,
                    'order' => $order
                ]));

            $this->mailer->send($email);

            $this->logger->info('Order confirmation email sent', [
                'customer_id' => $customer->getId(),
                'order_id' => $order->getId()
            ]);
        } catch (\Exception $e) {
            $this->logger->error('Failed to send order confirmation email', [
                'customer_id' => $customer->getId(),
                'error' => $e->getMessage()
            ]);
        }
    }

    public function sendWelcomeEmail(Customer $customer): void
    {
        $email = (new Email())
            ->from(new Address('noreply@example.com', 'Store Name'))
            ->to(new Address($customer->getEmail(), $customer->getFirstName()))
            ->subject('Welcome to Our Store!')
            ->html($this->twig->render('emails/welcome.html.twig', [
                'customer' => $customer
            ]));

        $this->mailer->send($email);
    }
}

// Controller usage
class OrderController extends AbstractController
{
    public function create(Request $request): Response
    {
        $order = $this->orderService->createFromCart($cart);

        $this->emailService->sendOrderConfirmation($customer, $order);

        $this->addFlash('success', 'Your order has been placed successfully!');

        return $this->redirectToRoute('order_confirmation', ['id' => $order->getId()]);
    }
}
```

---

### `zen_draw_form()` / `zen_draw_input_field()` → Symfony Form Component

**Legacy Pattern:**
```php
echo zen_draw_form('contact_us', zen_href_link(FILENAME_CONTACT_US, 'action=send'), 'post', 'id="contact_us"');
echo zen_draw_input_field('name', '', 'required');
echo zen_draw_textarea_field('message', '', '30', '10');
echo zen_draw_button('Submit', 'submit', 'type="submit"');
```

**Modern Symfony Pattern:**
```php
// Form Type
class ContactFormType extends AbstractType
{
    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        $builder
            ->add('name', TextType::class, [
                'required' => true,
                'attr' => ['required' => 'required']
            ])
            ->add('email', EmailType::class, [
                'required' => true
            ])
            ->add('message', TextareaType::class, [
                'required' => true,
                'attr' => ['rows' => 10]
            ])
            ->add('submit', SubmitType::class, [
                'label' => 'Submit'
            ]);
    }
}

// Controller
class ContactController extends AbstractController
{
    #[Route('/contact', name: 'contact')]
    public function contact(Request $request): Response
    {
        $form = $this->createForm(ContactFormType::class);

        $form->handleRequest($request);

        if ($form->isSubmitted() && $form->isValid()) {
            $data = $form->getData();

            $this->emailService->sendContactEmail($data);

            $this->addFlash('success', 'Your message has been sent!');

            return $this->redirectToRoute('contact');
        }

        return $this->render('contact/index.html.twig', [
            'form' => $form
        ]);
    }
}

// Twig template
{# templates/contact/index.html.twig #}
{{ form_start(form, {'attr': {'id': 'contact_form'}}) }}
    {{ form_row(form.name) }}
    {{ form_row(form.email) }}
    {{ form_row(form.message) }}
    {{ form_row(form.submit) }}
{{ form_end(form) }}
```

---

## Configuration

### `define()` constants → Symfony Parameters

**Legacy Pattern:**
```php
define('DIR_WS_CATALOG', '/');
define('DIR_WS_IMAGES', 'images/');
define('DIR_WS_INCLUDES', 'includes/');
define('DIR_FS_CATALOG', '/var/www/html/');
define('DIR_FS_LOGS', DIR_FS_CATALOG . 'logs/');
define('STORE_NAME', 'My Store');
define('STORE_OWNER', 'Store Owner');
define('STORE_OWNER_EMAIL_ADDRESS', 'owner@example.com');
define('EMAIL_FROM', '"Store Name" <noreply@example.com>');
```

**Modern Symfony Pattern:**
```php
# .env
CATALOG_URL=https://example.com
CATALOG_PATH=/var/www/html
IMAGES_PATH=%kernel.project_dir%/public/images
INCLUDES_PATH=%kernel.project_dir%/includes
LOG_PATH=%kernel.project_dir%/var/log
STORE_NAME="My Store"
STORE_EMAIL=noreply@example.com

# config/packages/parameters.yaml
parameters:
    catalog.url: '%env(CATALOG_URL)%'
    catalog.path: '%env(CATALOG_PATH)%'
    catalog.images_path: '%env(IMAGES_PATH)%'
    catalog.includes_path: '%env(INCLUDES_PATH)%'
    store.name: '%env(STORE_NAME)%'
    store.email: '%env(STORE_EMAIL)%'

// Service injection
class CatalogPathService
{
    public function __construct(
        #[Autowire('%catalog.images_path%')]
        private string $imagesPath,

        #[Autowire('%catalog.includes_path%')]
        private string $includesPath,

        #[Autowire('%kernel.project_dir%')]
        private string $projectDir
    ) {}

    public function getImageUrl(string $filename): string
    {
        return $this->imagesPath . '/' . $filename;
    }
}
```

---

## Summary Table

| Zen Cart Pattern | Symfony Hexagonal Equivalent |
|------------------|------------------------------|
| `zen_db_perform()` | Doctrine `persist()` + `flush()` |
| `zen_db_query()` | Doctrine QueryBuilder / DQL |
| `zen_db_prepare_input()` | Symfony Form Validation |
| `$_SESSION['customer_id']` | `TokenStorageInterface` + `UserInterface` |
| `$_SESSION['cart']` | `CartService` (DI) + Session |
| `zen_redirect()` | `RedirectResponse` / `redirectToRoute()` |
| `zen_href_link()` | `RouterInterface::generate()` |
| `zen_mail()` | Symfony Mailer + Twig templates |
| `zen_draw_form()` | Symfony Form Component |
| `define(DIR_WS_*)` | `.env` + parameters.yaml |
| `TABLE_*` constants | Doctrine Entity `@Table` |

---

## Anti-Patterns to Avoid

1. **Global Session Access** — Inject `SessionInterface` or use services
2. **Direct Database Calls in Controllers** — Use Application Services
3. **Raw SQL Queries** — Use Doctrine QueryBuilder/DQL
4. **Hardcoded Email Sending** — Use email service with templates
5. **Direct Form Rendering** — Use Symfony Form component
6. **Configuration in Code** — Use environment variables and parameters
7. **Global Message Stack** — Use Symfony Flash messages
8. **Entity Manager in Domain** — Keep entities pure, use repositories
