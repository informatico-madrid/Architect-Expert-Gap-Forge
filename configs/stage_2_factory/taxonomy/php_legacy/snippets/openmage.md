# OpenMage Anti-Patterns Mapping

This document provides specific modernization patterns for OpenMage (Magento 1 fork) legacy PHP applications, mapping common Magento patterns to their Symfony hexagonal architecture equivalents.

## Object Creation Patterns

### `Mage::getModel()` → DI Autowiring

**Legacy Pattern:**
```php
$product = Mage::getModel('catalog/product')->load($productId);
$category = Mage::getModel('catalog/category')->load($categoryId);
$order = Mage::getModel('sales/order')->load($orderId);

$products = Mage::getModel('catalog/product')->getCollection()
    ->addAttributeToSelect('*')
    ->addFieldToFilter('status', 1);
```

**Modern Symfony Pattern:**
```php
// Entity (Domain Model)
#[ORM\Entity]
#[ORM\Table(name: 'catalog_product_entity')]
class Product
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\Column(type: 'string', length: 255)]
    private string $sku;

    #[ORM\Column(type: 'string', length: 255)]
    private string $name;

    #[ORM\Column(type: 'decimal', precision: 12, scale: 4)]
    private float $price;

    #[ORM\Column(type: 'integer')]
    private int $status = 1;

    #[ORM\Column(type: 'datetime')]
    private ?DateTimeInterface $createdAt = null;

    #[ORM\Column(type: 'datetime')]
    private ?DateTimeInterface $updatedAt = null;

    // Getters and setters...
}

// Repository Interface (Driven Port)
interface ProductRepositoryInterface
{
    public function find(int $id): ?Product;
    public function findBySku(string $sku): ?Product;
    public function findActive(): array;
    public function save(Product $product): void;
    public function remove(Product $product): void;
}

// Repository Implementation (Driven Adapter)
class ProductRepository extends ServiceEntityRepository implements ProductRepositoryInterface
{
    public function __construct(RegistryInterface $registry)
    {
        parent::__construct(registry, Product::class);
    }

    public function find(int $id): ?Product
    {
        return $this->findOneBy(['id' => $id]);
    }

    public function findBySku(string $sku): ?Product
    {
        return $this->findOneBy(['sku' => $sku]);
    }

    public function findActive(): array
    {
        return $this->findBy(['status' => 1]);
    }

    public function save(Product $product): void
    {
        $this->getEntityManager()->persist($product);
        $this->getEntityManager()->flush();
    }
}

// Application Service (Use Case) with DI
class ProductService
{
    public function __construct(
        private ProductRepositoryInterface $productRepository,
        private CategoryRepositoryInterface $categoryRepository
    ) {}

    public function getProduct(int $productId): ?ProductDTO
    {
        $product = $this->productRepository->find($productId);

        if ($product === null) {
            return null;
        }

        return ProductDTO::fromEntity($product);
    }

    public function getActiveProducts(): array
    {
        return array_map(
            fn(Product $p) => ProductDTO::fromEntity($p),
            $this->productRepository->findActive()
        );
    }
}

// Controller with DI
class ProductController extends AbstractController
{
    public function __construct(
        private ProductService $productService
    ) {}

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

### `Mage::getSingleton()` → Service (Singleton Pattern via DI)

**Legacy Pattern:**
```php
// Creates or reuses singleton instance
$checkoutSession = Mage::getSingleton('checkout/session');
$cart = Mage::getSingleton('checkout/customer_session');
$catalogSession = Mage::getSingleton('catalog/session');

// Usage
$quote = $checkoutSession->getQuote();
$customer = $checkoutSession->getCustomer();
$cartItems = $checkoutSession->getQuote()->getAllItems();
```

**Modern Symfony Pattern:**
```php
// Register as service in config/services.yaml
# config/services.yaml
services:
    App\Application\Checkout\CheckoutSessionService:
        scope: request
        arguments:
            $session: '@session'
            $tokenStorage: '@security.token_storage'

    App\Application\Cart\CartService:
        arguments:
            $session: '@session'
            $quoteRepository: '@App\Infrastructure\Persistence\Doctrine\QuoteRepository'

// Singleton-like Service (scoped to request)
class CheckoutSessionService
{
    private ?Quote $quote = null;
    private ?Customer $customer = null;

    public function __construct(
        private SessionInterface $session,
        private TokenStorageInterface $tokenStorage,
        private QuoteRepositoryInterface $quoteRepository
    ) {
        $this->loadFromSession();
    }

    private function loadFromSession(): void
    {
        $quoteId = $this->session->get('quote_id');

        if ($quoteId !== null) {
            $this->quote = $this->quoteRepository->find($quoteId);
        }

        $token = $this->tokenStorage->getToken();
        if ($token !== null && $token->getUser() instanceof CustomerUser) {
            $this->customer = $token->getUser()->getCustomer();
        }
    }

    public function getQuote(): Quote
    {
        if ($this->quote === null) {
            $this->quote = new Quote();
            if ($this->customer !== null) {
                $this->quote->setCustomer($this->customer);
            }
        }

        return $this->quote;
    }

    public function getCustomer(): ?Customer
    {
        return $this->customer;
    }

    public function save(): void
    {
        $this->quoteRepository->save($this->quote);
        $this->session->set('quote_id', $this->quote->getId());
    }
}

// Cart Service (replaces checkout/cart singleton)
class CartService
{
    public function __construct(
        private SessionInterface $session,
        private QuoteRepositoryInterface $quoteRepository,
        private ProductRepositoryInterface $productRepository
    ) {}

    public function getCart(): Quote
    {
        $quoteId = $this->session->get('cart_quote_id');

        if ($quoteId !== null) {
            $quote = $this->quoteRepository->find($quoteId);
            if ($quote !== null && !$quote->isArchived()) {
                return $quote;
            }
        }

        return $this->createNewQuote();
    }

    public function addProduct(int $productId, int $qty = 1): Quote
    {
        $product = $this->productRepository->find($productId);

        if ($product === null) {
            throw new ProductNotFoundException($productId);
        }

        $quote = $this->getCart();

        // Check if product already in cart
        foreach ($quote->getItems() as $item) {
            if ($item->getProductId() === $productId) {
                $item->setQty($item->getQty() + $qty);
                $this->quoteRepository->save($quote);
                return $quote;
            }
        }

        // Add new item
        $quoteItem = new QuoteItem();
        $quoteItem->setProduct($product);
        $quoteItem->setQty($qty);
        $quoteItem->setQuote($quote);
        $quote->addItem($quoteItem);

        $this->quoteRepository->save($quote);
        $this->session->set('cart_quote_id', $quote->getId());

        return $quote;
    }

    private function createNewQuote(): Quote
    {
        $quote = new Quote();
        $this->quoteRepository->save($quote);
        $this->session->set('cart_quote_id', $quote->getId());

        return $quote;
    }
}
```

---

### `Varien_Object` → Typed DTO

**Legacy Pattern:**
```php
// Varien_Object as generic data container
$product = Mage::getModel('catalog/product');
$product->setName('Test Product');
$product->setPrice(99.99);
$product->setData('custom_attribute', 'value');

// Varien_Data_Collection for collections
$collection = Mage::getModel('catalog/product')->getCollection();
foreach ($collection as $item) {
    echo $item->getName();
}
```

**Modern Symfony Pattern:**
```php
// DTO (Data Transfer Object) - immutable
class ProductDTO
{
    public function __construct(
        public readonly int $id,
        public readonly string $sku,
        public readonly string $name,
        public readonly float $price,
        public readonly string $status,
        public readonly ?DateTimeInterface $createdAt,
        public readonly ?DateTimeInterface $updatedAt
    ) {}

    public static function fromEntity(Product $product): self
    {
        return new self(
            id: $product->getId(),
            sku: $product->getSku(),
            name: $product->getName(),
            price: $product->getPrice(),
            status: $product->getStatus() === 1 ? 'enabled' : 'disabled',
            createdAt: $product->getCreatedAt(),
            updatedAt: $product->getUpdatedAt()
        );
    }

    public function toArray(): array
    {
        return [
            'id' => $this->id,
            'sku' => $this->sku,
            'name' => $this->name,
            'price' => $this->price,
            'status' => $this->status,
            'created_at' => $this->createdAt?->format('Y-m-d H:i:s'),
            'updated_at' => $this->updatedAt?->format('Y-m-d H:i:s')
        ];
    }
}

// Write DTO for input
class CreateProductDTO
{
    public function __construct(
        public readonly string $sku,
        public readonly string $name,
        public readonly float $price,
        public readonly ?string $description = null,
        public readonly array $categories = []
    ) {}

    public static function fromRequest(Request $request): self
    {
        return new self(
            sku: $request->request->get('sku'),
            name: $request->request->get('name'),
            price: (float) $request->request->get('price'),
            description: $request->request->get('description'),
            categories: $request->request->get('categories', [])
        );
    }
}

// Collection DTO
class ProductListDTO
{
    public function __construct(
        public readonly array $items,
        public readonly int $totalCount,
        public readonly int $page,
        public readonly int $pageSize
    ) {}

    public static function fromEntities(array $products, int $page, int $pageSize): self
    {
        return new self(
            items: array_map(fn(Product $p) => ProductDTO::fromEntity($p), $products),
            totalCount: count($products),
            page: $page,
            pageSize: $pageSize
        );
    }
}
```

---

## Database Access Patterns

### Resource Models → Doctrine Repository

**Legacy Pattern:**
```php
// Resource Model (Mage_Catalog_Model_Resource_Product)
$product = Mage::getModel('catalog/product')->load($id);

// Direct resource model usage
$resource = Mage::getResourceModel('catalog/product');
$products = $resource->getProductsByCategories($categoryIds);

// Collection (Mage_Catalog_Model_Resource_Product_Collection)
$collection = Mage::getModel('catalog/product')->getCollection()
    ->addAttributeToSelect(['name', 'price', 'image'])
    ->addAttributeToFilter('status', 1)
    ->addAttributeToFilter('visibility', ['in' => [2, 3, 4]])
    ->addUrlRewrite()
    ->setOrder('name', 'ASC')
    ->setPageSize(20)
    ->setCurPage(1);

// SQL logging
$collection->printLogQuery(true);
```

**Modern Symfony Pattern:**
```php
// Entity
#[ORM\Entity]
#[ORM\Table(name: 'catalog_product_entity')]
#[ORM\HasLifecycleCallbacks]
class Product
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\Column(type: 'string', length: 255, unique: true)]
    private string $sku;

    #[ORM\OneToMany(mappedBy: 'product', targetEntity: ProductAttributeValue::class)]
    private Collection $attributeValues;

    #[ORM\ManyToMany(targetEntity: Category::class, inversedBy: 'products')]
    #[ORM\JoinTable(name: 'catalog_product_category')]
    private Collection $categories;

    #[ORM\OneToMany(mappedBy: 'product', targetEntity: ProductUrlRewrite::class)]
    private Collection $urlRewrites;

    public function __construct()
    {
        $this->attributeValues = new ArrayCollection();
        $this->categories = new ArrayCollection();
        $this->urlRewrites = new ArrayCollection();
    }

    #[ORM\PrePersist]
    public function prePersist(): void
    {
        $this->createdAt = new DateTimeImmutable();
    }
}

// Repository with QueryBuilder
class ProductRepository extends ServiceEntityRepository implements ProductRepositoryInterface
{
    public function __construct(RegistryInterface $registry)
    {
        parent::__construct($registry, Product::class);
    }

    public function findVisible(): array
    {
        return $this->createQueryBuilder('p')
            ->andWhere('p.status = :status')
            ->andWhere('p.visibility IN (:visibility)')
            ->setParameter('status', 1)
            ->setParameter('visibility', [2, 3, 4])
            ->orderBy('p.name', 'ASC')
            ->getQuery()
            ->getResult();
    }

    public function findByCategories(array $categoryIds): array
    {
        return $this->createQueryBuilder('p')
            ->innerJoin('p.categories', 'c')
            ->andWhere('c.id IN (:categoryIds)')
            ->setParameter('categoryIds', $categoryIds)
            ->getQuery()
            ->getResult();
    }

    public function findWithUrlRewrite(): array
    {
        return $this->createQueryBuilder('p')
            ->innerJoin('p.urlRewrites', 'u')
            ->andWhere('u.store = :store')
            ->setParameter('store', 1)
            ->getQuery()
            ->getResult();
    }

    public function findPaginated(int $page, int $pageSize): array
    {
        return $this->createQueryBuilder('p')
            ->setFirstResult(($page - 1) * $pageSize)
            ->setMaxResults($pageSize)
            ->orderBy('p.name', 'ASC')
            ->getQuery()
            ->getResult();
    }

    public function countAll(): int
    {
        return $this->createQueryBuilder('p')
            ->select('COUNT(p.id)')
            ->getQuery()
            ->getSingleScalarResult();
    }
}
```

---

### `Mage::getResourceModel()` → Doctrine QueryBuilder

**Legacy Pattern:**
```php
$resource = Mage::getResourceModel('catalog/product_collection');
$resource->addAttributeToSelect('*')
    ->addFieldToFilter('status', ['eq' => 1]);

// Direct table queries
$readConnection = Mage::getSingleton('core/resource')->getConnection('core_read');
$select = $readConnection->select()
    ->from(['e' => 'catalog_product_entity'])
    ->joinLeft(
        ['p' => 'catalog_product_entity_varchar'],
        'e.entity_id = p.entity_id AND p.attribute_id = 71',
        ['name' => 'value']
    )
    ->where('e.entity_id = ?', $productId);

$row = $readConnection->fetchRow($select);
```

**Modern Symfony Pattern:**
```php
class ProductQueryService
{
    public function __construct(
        private EntityManagerInterface $em
    ) {}

    public function getProductWithAttributes(int $productId): ?array
    {
        $query = $this->em->createQuery('
            SELECT p, av
            FROM App\Domain\Product\Entity\Product p
            LEFT JOIN p.attributeValues av
            WHERE p.id = :id
        ')->setParameter('id', $productId);

        return $query->getOneOrNullResult();
    }

    public function searchProducts(string $searchTerm, int $limit = 20): array
    {
        return $this->em->createQueryBuilder()
            ->select('p')
            ->from(Product::class, 'p')
            ->where('p.name LIKE :search')
            ->orWhere('p.sku LIKE :search')
            ->setParameter('search', "%{$searchTerm}%")
            ->setMaxResults($limit)
            ->getQuery()
            ->getResult();
    }

    public function getProductsByAttributeSet(int $attributeSetId): array
    {
        return $this->createQueryBuilder()
            ->select('p')
            ->from(Product::class, 'p')
            ->andWhere('p.attributeSet = :setId')
            ->setParameter('setId', $attributeSetId)
            ->getQuery()
            ->getResult();
    }
}
```

---

## Configuration & Registry

### `Mage::getStoreConfig()` → Symfony ParameterBag

**Legacy Pattern:**
```php
$storeName = Mage::getStoreConfig('general/store_information/name');
$currency = Mage::getStoreConfig('currency/options/base');
$logo = Mage::getStoreConfig('design/header/logo_src');

// In templates
echo Mage::getStoreConfig('design/head/title_prefix');
```

**Modern Symfony Pattern:**
```php
# config/packages/store.yaml
parameters:
    store:
        name: '%env(STORE_NAME)%'
        email: '%env(STORE_EMAIL)%'
        currency:
            base: '%env(BASE_CURRENCY)%'
            allowed: '%env(ALLOWED_CURRENCIES)%'
        logo: '%env(STORE_LOGO)%'

# .env
STORE_NAME="OpenMage Store"
STORE_EMAIL=contact@example.com
BASE_CURRENCY=USD
ALLOWED_CURRENCIES="USD,EUR,GBP"
STORE_LOGO="/images/logo.png"

// Service injection
class StoreConfigService
{
    public function __construct(
        #[Autowire('%store.name%')]
        private string $storeName,

        #[Autowire('%store.email%')]
        private string $storeEmail,

        #[Autowire('%store.currency.base%')]
        private string $baseCurrency
    ) {}

    public function getStoreName(): string
    {
        return $this->storeName;
    }

    public function getBaseCurrency(): string
    {
        return $this->baseCurrency;
    }
}

// Twig global
# config/packages/twig.yaml
twig:
    globals:
        store_config: '@App\Application\Config\StoreConfigService'
```

---

### `Mage::register()` / `Mage::registry()` → Symfony Services

**Legacy Pattern:**
```php
// Register global objects
Mage::register('current_product', $product);
Mage::register('current_category', $category);
Mage::register('current_customer', $customer);

// Retrieve registered objects
$product = Mage::registry('current_product');
$category = Mage::registry('current_category');

// Registry with singleton
Mage::register('singleton_key', $object, true);
```

**Modern Symfony Pattern:**
```php
// Context Services instead of Registry
class ProductContextService
{
    private ?Product $currentProduct = null;
    private ?Category $currentCategory = null;

    public function setCurrentProduct(Product $product): void
    {
        $this->currentProduct = $product;
    }

    public function getCurrentProduct(): ?Product
    {
        return $this->currentProduct;
    }

    public function setCurrentCategory(Category $category): void
    {
        $this->currentCategory = $category;
    }

    public function getCurrentCategory(): ?Category
    {
        return $this->currentCategory;
    }
}

// Register as service
# config/services.yaml
services:
    App\Application\Context\ProductContextService:
        scope: request
        tags:
            - { name: kernel.request, priority: 100 }

// Usage in Controller
class ProductController extends AbstractController
{
    public function __construct(
        private ProductContextService $productContext
    ) {}

    #[Route('/product/{id}', name: 'product_show')]
    public function show(int $id): Response
    {
        $product = $this->productRepository->find($id);

        if ($product === null) {
            throw $this->createNotFoundException();
        }

        // Set in context for downstream services
        $this->productContext->setCurrentProduct($product);

        return $this->render('product/show.html.twig', [
            'product' => ProductDTO::fromEntity($product)
        ]);
    }
}
```

---

## Summary Table

| OpenMage Pattern | Symfony Hexagonal Equivalent |
|------------------|------------------------------|
| `Mage::getModel()` | Constructor injection + Repository |
| `Mage::getSingleton()` | Service (scoped to request/container) |
| `Varien_Object` | Typed DTO (immutable) |
| `Mage_Catalog_Model_Resource_Product` | Doctrine Repository |
| `Mage::getResourceModel()` | Doctrine QueryBuilder/DQL |
| `Mage::getStoreConfig()` | ParameterBag + `.env` |
| `Mage::registry()` | Context Services |
| `Mage::register()` | Setter injection in Context Services |
| Product Collection | Doctrine `QueryBuilder::getResult()` |
| Varien_Data_Collection | Typed Collection DTOs |

---

## Anti-Patterns to Avoid

1. **Global Static Access** — Use dependency injection everywhere
2. **Registry Pattern** — Replace with context services scoped to request
3. **Singleton Abuse** — Use scoped services instead
4. **Varien_Object Flexibility** — Use strict typed DTOs
5. **EAV Tables** — Normalize to proper relational schema
6. **Flat Tables for Collections** — Use proper entity relationships
7. **Direct Resource Model in Controllers** — Use application services
8. **Store Config in Business Logic** — Inject configuration services
