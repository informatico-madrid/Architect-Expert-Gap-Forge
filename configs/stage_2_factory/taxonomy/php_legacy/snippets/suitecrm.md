# SuiteCRM Anti-Patterns Mapping

This document provides specific modernization patterns for SuiteCRM legacy PHP applications, mapping common SuiteCRM patterns to their Symfony hexagonal architecture equivalents.

## Database Access Patterns

### `SugarBean::retrieve()` → Doctrine Repository

**Legacy Pattern:**
```php
// Retrieve a bean by ID
$contact = BeanFactory::getBean('Contacts', $contact_id);
$contact = SugarBean::retrieve($contact_id);

// Retrieve with relationships
$account = BeanFactory::getBean('Accounts', $account_id);
$account->load_relationship('contacts');
$contacts = $account->get_linked_beans();

// Retrieve with specific fields
$bean = SugarBean::retrieve();
$bean->retrieve($id);
$bean->fetchFromDB($id);

// Retrieve from relationship
$opportunity = $account->opportunities[$index];

// Query-based retrieval
$bean = SugarBean::getBean('Accounts');
$bean->retrieve($_REQUEST['record']);

// Using list queries
$seed = BeanFactory::getBean('Accounts');
$where = "accounts.name LIKE 'A%'";
$list = $seed->get_list($where);
```

**Modern Symfony Pattern:**
```php
// Repository (Driven Port Implementation)
class ContactRepository implements ContactRepositoryInterface
{
    public function __construct(
        private EntityManagerInterface $em
    ) {}

    public function findById(int $id): ?Contact
    {
        return $this->em->find(Contact::class, $id);
    }

    public function findByEmail(string $email): ?Contact
    {
        return $this->em->createQueryBuilder()
            ->select('c')
            ->from(Contact::class, 'c')
            ->where('c.email = :email')
            ->setParameter('email', $email)
            ->getQuery()
            ->getOneOrNullResult();
    }

    public function findAll(): array
    {
        return $this->em->getRepository(Contact::class)->findAll();
    }

    public function findByNameLike(string $namePattern): array
    {
        return $this->em->createQueryBuilder()
            ->select('c')
            ->from(Contact::class, 'c')
            ->where('c.name LIKE :pattern')
            ->setParameter('pattern', $namePattern)
            ->getQuery()
            ->getResult();
    }

    public function findByAccount(Account $account): array
    {
        return $this->em->createQueryBuilder()
            ->select('c')
            ->from(Contact::class, 'c')
            ->where('c.account = :account')
            ->setParameter('account', $account)
            ->getQuery()
            ->getResult();
    }
}

// Use Case / Application Service
class ContactManagementService
{
    public function __construct(
        private ContactRepositoryInterface $contactRepository
    ) {}

    public function getContact(int $id): ?Contact
    {
        return $this->contactRepository->findById($id);
    }

    public function getContactsByAccount(Account $account): array
    {
        return $this->contactRepository->findByAccount($account);
    }

    public function searchContacts(string $query): array
    {
        return $this->contactRepository->findByNameLike("%{$query}%");
    }
}

// Controller
class ContactController extends AbstractController
{
    public function __construct(
        private ContactRepositoryInterface $contactRepository
    ) {}

    #[Route('/contacts/{id}', name: 'contact_show')]
    public function show(int $id): Response
    {
        $contact = $this->contactRepository->findById($id);

        if (!$contact) {
            throw $this->createNotFoundException('Contact not found');
        }

        return $this->render('contact/show.html.twig', [
            'contact' => $contact
        ]);
    }
}
```

---

### `DBManager::getConnection()` → Doctrine DBAL

**Legacy Pattern:**
```php
// Direct database connection
$db = DBManagerFactory::getInstance();
$conn = $db->getConnection();

// Execute query
$result = $db->query("SELECT * FROM accounts WHERE deleted = 0");
$row = $db->fetchByAssoc($result);

// Using sqrv
$query = "SELECT * FROM contacts WHERE account_id = ?";
$result = $db->query($query, array($account_id));

// Fetch rows
while ($row = $db->fetchByAssoc($result)) {
    $data[] = $row;
}

// Get a single value
$value = $db->getOne("SELECT COUNT(*) FROM accounts WHERE deleted = 0");

// Get a row
$row = $db->getRow("SELECT * FROM accounts WHERE id = ?", array($id));

// Get an array of rows
$rows = $db->fetchAll("SELECT * FROM accounts");

// Using lists
$bean = BeanFactory::getBean('Accounts');
$query = $bean->create_new_list_query('', $where);

// Raw SQL
$sql = "UPDATE accounts SET name = '{$name}' WHERE id = '{$id}'";
$db->query($sql);
```

**Modern Symfony Pattern:**
```php
// Doctrine DBAL Connection (replaces DBManager::getConnection)
class AccountRepository implements AccountRepositoryInterface
{
    public function __construct(
        private EntityManagerInterface $em
    ) {}

    public function findActive(): array
    {
        return $this->em->createQueryBuilder()
            ->select('a')
            ->from(Account::class, 'a')
            ->where('a.deleted = :deleted')
            ->setParameter('deleted', false)
            ->getQuery()
            ->getResult();
    }

    public function countAll(): int
    {
        return $this->em->createQueryBuilder()
            ->select('COUNT(a)')
            ->from(Account::class, 'a')
            ->where('a.deleted = :deleted')
            ->setParameter('deleted', false)
            ->getQuery()
            ->getSingleScalarResult();
    }

    public function findById(string $id): ?Account
    {
        return $this->em->find(Account::class, $id);
    }

    // For complex raw queries (replaces direct $db->query)
    public function findByCustomWhere(string $whereClause, array $params): array
    {
        $conn = $this->em->getConnection();
        $sql = "SELECT * FROM accounts WHERE deleted = 0 AND " . $whereClause;

        return $conn->fetchAllAssociative($sql, $params);
    }

    // For complex aggregates (replaces $db->getOne)
    public function getAccountCountByIndustry(string $industry): int
    {
        return $this->em->createQueryBuilder()
            ->select('COUNT(a)')
            ->from(Account::class, 'a')
            ->where('a.industry = :industry')
            ->andWhere('a.deleted = :deleted')
            ->setParameter('industry', $industry)
            ->setParameter('deleted', false)
            ->getQuery()
            ->getSingleScalarResult();
    }
}

// Service for complex queries
class ReportingService
{
    public function __construct(
        private EntityManagerInterface $em
    ) {}

    public function getAccountsByIndustry(): array
    {
        $conn = $this->em->getConnection();

        $sql = "SELECT industry, COUNT(*) as count
                FROM accounts
                WHERE deleted = 0
                GROUP BY industry
                ORDER BY count DESC";

        return $conn->fetchAllAssociative($sql);
    }

    public function executeRawUpdate(string $sql, array $params): int
    {
        $conn = $this->em->getConnection();

        return $conn->executeStatement($sql, $params);
    }
}
```

---

## Bean Factory Pattern

### `BeanFactory::getBean()` → Dependency Injection

**Legacy Pattern:**
```php
// Get beans via factory
$contact = BeanFactory::getBean('Contacts', $id);
$account = BeanFactory::getBean('Accounts', $account_id);
$lead = BeanFactory::getBean('Leads', $lead_id);

// Get with specific module
$bean = BeanFactory::getBean('Opportunities', $opp_id);

// With custom relationships
$bean = BeanFactory::getBean('Accounts', $id);
$bean->load_relationship('contacts');

// Reuse existing beans
global $beanList, $beanFiles;
$bean = new $beanFiles['Accounts']();

// In controllers
$bean = BeanFactory::getBean('Cases', $_REQUEST['record']);

// From relationships
$notes = $contact->get_linked_beans('notes', 'Note');
$notes = $contact->get_notes();

// Create new beans
$bean = BeanFactory::newBean('Accounts');
$bean->name = 'New Account';
$bean->save();

// Bean hierarchy
class Contact extends SugarBean {
    // Contact-specific logic
}
$contact = new Contact();
```

**Modern Symfony Pattern:**
```php
// Service Definition (replaces BeanFactory::getBean)
# config/services.yaml
services:
    App\Persistence\Repository\ContactRepository:
        autowire: true
        tags: ['doctrine.repository']

    App\Persistence\Repository\AccountRepository:
        autowire: true
        tags: ['doctrine.repository']

    App\Domain\Contact\ContactService:
        autowire: true
        arguments:
            - '@App\Persistence\Repository\ContactRepository'

    App\Domain\Account\AccountService:
        autowire: true
        arguments:
            - '@App\Persistence\Repository\AccountRepository'

// Controller with DI (replaces BeanFactory::getBean in controllers)
class ContactController extends AbstractController
{
    public function __construct(
        private ContactRepositoryInterface $contactRepository,
        private ContactServiceInterface $contactService
    ) {}

    #[Route('/contacts/{id}', name: 'contact_show')]
    public function show(int $id): Response
    {
        $contact = $this->contactRepository->findById($id);

        if (!$contact) {
            throw $this->createNotFoundException('Contact not found');
        }

        return $this->render('contact/show.html.twig', [
            'contact' => $contact
        ]);
    }

    #[Route('/contacts/create', name: 'contact_create')]
    public function create(Request $request): Response
    {
        $contact = $this->contactService->createContact(
            $request->request->get('first_name'),
            $request->request->get('last_name'),
            $request->request->get('email')
        );

        return $this->redirectToRoute('contact_show', ['id' => $contact->getId()]);
    }
}

// Domain Service (replaces business logic in SugarBean)
class ContactService implements ContactServiceInterface
{
    public function __construct(
        private ContactRepositoryInterface $contactRepository,
        private EventDispatcherInterface $eventDispatcher
    ) {}

    public function createContact(string $firstName, string $lastName, string $email): Contact
    {
        $contact = new Contact();
        $contact->setFirstName($firstName);
        $contact->setLastName($lastName);
        $contact->setEmail($email);

        $this->contactRepository->save($contact);

        $this->eventDispatcher->dispatch(new ContactCreatedEvent($contact));

        return $contact;
    }

    public function findWithAccounts(int $contactId): ?Contact
    {
        $contact = $this->contactRepository->find($contactId);

        if ($contact && $contact->getAccount()) {
            // Relationships loaded via Doctrine
        }

        return $contact;
    }
}

// Factory for complex creation (replaces BeanFactory::newBean)
class ContactFactory implements ContactFactoryInterface
{
    public function __construct(
        private EntityManagerInterface $em
    ) {}

    public function createForAccount(Account $account, string $firstName, string $lastName): Contact
    {
        $contact = new Contact();
        $contact->setAccount($account);
        $contact->setFirstName($firstName);
        $contact->setLastName($lastName);
        $contact->setCreatedAt(new DateTimeImmutable());

        $this->em->persist($contact);
        $this->em->flush();

        return $contact;
    }
}
```

---

## Caching Patterns

### `sugar_cache_*` → Symfony Cache

**Legacy Pattern:**
```php
// Simple cache
sugar_cache_put('my_key', $value);
$value = sugar_cache_get('my_key');

// Clear cache
sugar_cache_clear();

// Clear specific entry
sugar_cache_clear('my_key');

// Using with timeout
sugar_cache_put('config_data', $data, 300);

// Session cache
sugar_cache_put('user_preferences_' . $user_id, $prefs);

// With namespace
sugar_cache_put('accounts_list', $accounts, 3600);

// Cache statistics
$stats = sugar_cache_get_stats();

// Object caching
$sugarCache = SugarCache::instance();
$sugarCache->set('key', $value);

// Data list cache
$cacheKey = 'accounts_related_' . $account_id;
if (sugar_cache_exists($cacheKey)) {
    $data = sugar_cache_get($cacheKey);
} else {
    $data = $this->fetchData($account_id);
    sugar_cache_put($cacheKey, $data);
}
```

**Modern Symfony Pattern:**
```php
// Symfony Cache (replaces sugar_cache_*)
use Symfony\Component\Cache\Adapter\RedisAdapter;
use Symfony\Component\Cache\Adapter\ApcuAdapter;
use Symfony\Contracts\Cache\ItemInterface;

// Cache Service
class CacheService
{
    public function __construct(
        private CacheInterface $cache
    ) {}

    public function get(string $key, callable $callback, ?float $maxAge = null): mixed
    {
        return $this->cache->get($key, function (ItemInterface $item) use ($callback, $maxAge) {
            if ($maxAge) {
                $item->expiresAfter($maxAge);
            }

            return $callback();
        });
    }

    public function set(string $key, mixed $value, ?float $maxAge = null): void
    {
        $item = $this->cache->getItem($key);

        if ($maxAge) {
            $item->expiresAfter($maxAge);
        }

        $item->set($value);
        $this->cache->save($item);
    }

    public function delete(string $key): void
    {
        $this->cache->deleteItem($key);
    }

    public function clear(): void
    {
        $this->cache->clear();
    }

    public function has(string $key): bool
    {
        return $this->cache->hasItem($key);
    }
}

// Configuration
# config/packages/cache.yaml
framework:
    cache:
        app: cache.adapter.redis
        default_redis_provider: '%env(REDIS_URL)%'
        pools:
            cache.account_data:
                adapter: cache.adapter.redis
                max_items: 1000

            cache.user_preferences:
                adapter: cache.adapter.apcu
                max_items: 500

// Using in Services (replaces sugar_cache_put/get)
class AccountService
{
    public function __construct(
        private AccountRepositoryInterface $accountRepository,
        private CacheInterface $cache
    ) {}

    public function getAccountsList(): array
    {
        return $this->cache->get('accounts_list', function (ItemInterface $item) {
            $item->expiresAfter(3600); // 1 hour

            return $this->accountRepository->findAllActive();
        });
    }

    public function getAccountById(string $id): ?Account
    {
        $cacheKey = 'account_' . $id;

        return $this->cache->get($cacheKey, function (ItemInterface $item) use ($id) {
            $item->expiresAfter(1800); // 30 minutes

            return $this->accountRepository->findById($id);
        });
    }

    public function invalidateAccountCache(string $id): void
    {
        $this->cache->deleteItem('account_' . $id);
        $this->cache->deleteItem('accounts_list');
    }
}

// User Preferences Service (replaces sugar_cache_put with user_id)
class UserPreferenceService
{
    public function __construct(
        private CacheInterface $cache
    ) {}

    public function getPreferences(int $userId): array
    {
        $key = 'user_preferences_' . $userId;

        return $this->cache->get($key, function (ItemInterface $item) use ($userId) {
            $item->expiresAfter(86400); // 24 hours

            // Load from database
            return $this->loadFromDatabase($userId);
        });
    }

    public function setPreference(int $userId, string $key, mixed $value): void
    {
        $prefs = $this->getPreferences($userId);
        $prefs[$key] = $value;

        $this->cache->deleteItem('user_preferences_' . $userId);
        $this->saveToDatabase($userId, $prefs);
    }
}
```

---

## Global State Patterns

### `global $db` → DI Database Service

**Legacy Pattern:**
```php
// Global database access
global $db;
$result = $db->query($sql);

// Global current user
global $current_user;
$user_id = $current_user->id;
$user_name = $current_user->user_name;

// Global app config
global $app_strings;
$label = $app_strings['LBL_SAVE'];

// Global app list strings
global $app_list_strings;
$module_list = $app_list_strings['moduleList'];

// Global bean
global $focus;
$focus->name = 'Test';

// Global configuration
global $sugar_config;
$cache_dir = $sugar_config['cache_dir'];

// In custom logic
function my_function() {
    global $db, $current_user;
    $user_id = $current_user->id;
    $db->query("UPDATE accounts SET modified_user_id = '$user_id'");
}
```

**Modern Symfony Pattern:**
```php
// Dependency Injection (replaces global $db, $current_user)
class AccountController extends AbstractController
{
    public function __construct(
        private AccountRepositoryInterface $accountRepository,
        private UserInterface $currentUser
    ) {}

    #[Route('/accounts/create', name: 'account_create')]
    public function create(Request $request): Response
    {
        // Replace global $current_user
        $userId = $this->currentUser->getId();

        $account = new Account();
        $account->setName($request->request->get('name'));
        $account->setModifiedBy($this->currentUser);

        $this->accountRepository->save($account);

        return $this->json(['id' => $account->getId()]);
    }
}

// Service with explicit dependencies
class AccountService
{
    public function __construct(
        private EntityManagerInterface $em,
        private UserRepositoryInterface $userRepository,
        private LoggerInterface $logger
    ) {}

    public function updateAccount(Account $account, array $data): void
    {
        // Replace global $db with EntityManager
        foreach ($data as $field => $value) {
            $setter = 'set' . ucfirst($field);
            if (method_exists($account, $setter)) {
                $account->$setter($value);
            }
        }

        $account->setModifiedAt(new DateTimeImmutable());

        $this->em->flush();
    }
}

// Configuration Service (replaces global $app_strings)
class LocalizationService
{
    public function __construct(
        private TranslationServiceInterface $translator
    ) {}

    public function getLabel(string $key): string
    {
        return $this->translator->trans($key);
    }

    public function getModuleList(): array
    {
        return $this->translator->trans('module_list');
    }
}

// Config Service (replaces global $sugar_config)
class ConfigService
{
    public function __construct(
        private ParameterBagInterface $params
    ) {}

    public function getCacheDir(): string
    {
        return $this->params->get('sugar_config.cache_dir', '/var/cache');
    }

    public function get(string $key, mixed $default = null): mixed
    {
        return $this->params->get('sugar_config.' . $key, $default);
    }
}

// Function wrapper for legacy code
function createScopedServices(): array
{
    // For compatibility with legacy function wrappers
    global $container;

    return [
        'db' => $container->get(EntityManagerInterface::class),
        'current_user' => $container->get(TokenStorageInterface::class)->getToken()?->getUser(),
        'app_strings' => $container->get(TranslationServiceInterface::class),
    ];
}
```

---

## Vardef & Module Patterns

### `vardef` arrays → Doctrine Entity Metadata

**Legacy Pattern:**
```php
// vardef.php definition
$dictionary['Account'] = array(
    'table' => 'accounts',
    'fields' => array(
        'name' => array(
            'name' => 'name',
            'type' => 'varchar',
            'len' => 255,
            'required' => true,
        ),
        'industry' => array(
            'name' => 'industry',
            'type' => 'enum',
            'options' => 'industry_dom',
        ),
    ),
    'indices' => array(
        array(
            'name' => 'idx_account_name',
            'type' => 'index',
            'fields' => array('name'),
        ),
    ),
    'relationships' => array(
        'account_contacts' => array(
            'lhs_module' => 'Accounts',
            'rhs_module' => 'Contacts',
            'relationship_type' => 'one-to-many',
        ),
    ),
);

// In SugarBean
class Account extends SugarBean {
    var $table_name = 'accounts';
    var $object_name = 'Account';
    var $module_dir = 'Accounts';
    var $new_schema = true;
}
```

**Modern Symfony Pattern:**
```php
// Doctrine Entity (replaces vardef arrays)
#[ORM\Entity(repositoryClass: AccountRepository::class)]
#[ORM\Table(name: 'accounts')]
class Account
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\Column(type: 'string', length: 255)]
    #[ORM\Column(nullable: false)]
    private string $name;

    #[ORM\Column(type: 'string', length: 100, nullable: true)]
    #[ORM\Column(options: ['default' => null])]
    private ?string $industry = null;

    #[ORM\Column(name: 'date_entered', type: 'datetime')]
    private DateTimeInterface $dateEntered;

    #[ORM\ManyToOne(targetEntity: User::class)]
    #[ORM\JoinColumn(name: 'assigned_user_id', referencedColumnName: 'id')]
    private ?User $assignedUser = null;

    #[ORM\OneToMany(mappedBy: 'account', targetEntity: Contact::class)]
    private Collection $contacts;

    #[ORM\OneToMany(mappedBy: 'account', targetEntity: Opportunity::class)]
    private Collection $opportunities;

    #[ORM\Index(columns: ['name'], name: 'idx_account_name')]
    // Getters and setters
}

// Enum type for industry (replaces $app_list_strings['industry_dom'])
#[ORM\EnumType(class: IndustryEnum::class)]
#[ORM\Column(type: 'enum')]
class IndustryEnum extends Enum
{
    const TECHNOLOGY = 'Technology';
    const FINANCE = 'Finance';
    const HEALTHCARE = 'Healthcare';
    const MANUFACTURING = 'Manufacturing';
    const RETAIL = 'Retail';
    const OTHER = 'Other';
}

// Relationships (replaces relationship definitions)
class Contact
{
    #[ORM\ManyToOne(targetEntity: Account::class, inversedBy: 'contacts')]
    #[ORM\JoinColumn(name: 'account_id', referencedColumnName: 'id')]
    private ?Account $account = null;

    public function getAccount(): ?Account
    {
        return $this->account;
    }

    public function setAccount(?Account $account): self
    {
        $this->account = $account;
        return $this;
    }
}
```

---

## ACL & Security Patterns

### ACL checks → Symfony Voters

**Legacy Pattern:**
```php
// ACL check
if (!ACLController::checkAccess('Accounts', 'edit', true)) {
    return;
}

// Module access
if (!$current_user->hasAccess('Accounts', 'view')) {
   SugarApplication::end();
}

// Field level
$fieldACL = ACLField::hasAccess('Accounts', 'edit', 'amount', $current_user->id);

// Role check
$role = new ACLRole();
$roles = $role->getUserRoles($current_user->id);

// Object level
$bean->ACLAllowOwner;
$bean->ACLAccess;
```

**Modern Symfony Pattern:**
```php
// Symfony Voter (replaces ACLController::checkAccess)
#[AsVoter]
class AccountVoter extends Voter
{
    public const VIEW = 'VIEW';
    public const EDIT = 'EDIT';
    public const DELETE = 'DELETE';

    protected function supports(string $attribute, mixed $subject): bool
    {
        return $subject instanceof Account
            && in_array($attribute, [self::VIEW, self::EDIT, self::DELETE]);
    }

    protected function voteOnAttribute(string $attribute, mixed $subject, TokenInterface $token): bool
    {
        $user = $token->getUser();

        if (!$user instanceof UserInterface) {
            return false;
        }

        // Check if user is owner
        if ($subject instanceof OwnableInterface && $subject->getOwner() === $user) {
            return true;
        }

        // Admin users have full access
        if (in_array('ROLE_ADMIN', $user->getRoles())) {
            return true;
        }

        // Check permission based on attribute
        return match ($attribute) {
            self::VIEW => $this->canView($user),
            self::EDIT => $this->canEdit($user),
            self::DELETE => $this->canDelete($user),
            default => false,
        };
    }

    private function canView(User $user): bool
    {
        return $user->hasPermission('account:read');
    }

    private function canEdit(User $user): bool
    {
        return $user->hasPermission('account:write');
    }

    private function canDelete(User $user): bool
    {
        return $user->hasPermission('account:delete');
    }
}

// Controller with authorization
class AccountController extends AbstractController
{
    #[Route('/accounts/{id}', name: 'account_show')]
    public function show(Account $account): Response
    {
        // Replaces ACLController::checkAccess('Accounts', 'view')
        $this->denyAccessUnlessGranted(AccountVoter::VIEW, $account);

        return $this->render('account/show.html.twig', [
            'account' => $account
        ]);
    }

    #[Route('/accounts/{id}/edit', name: 'account_edit')]
    public function edit(Account $account, Request $request): Response
    {
        $this->denyAccessUnlessGranted(AccountVoter::EDIT, $account);

        // Process form
    }

    #[Route('/accounts/{id}', name: 'account_delete')]
    #[Method('DELETE')]
    public function delete(Account $account): Response
    {
        $this->denyAccessUnlessGranted(AccountVoter::DELETE, $account);

        // Delete account
    }
}

// Field-level security (replaces ACLField::hasAccess)
class FinancialDataVoter extends Voter
{
    protected function supports(string $attribute, mixed $subject): bool
    {
        return $subject instanceof FinancialDataInterface;
    }

    protected function voteOnAttribute(string $attribute, mixed $subject, TokenInterface $token): bool
    {
        $user = $token->getUser();

        // Check if user has finance role
        return $user->hasRole('ROLE_FINANCE');
    }
}
```

---

## Summary Table

| SuiteCRM Pattern | Symfony Hexagonal Equivalent |
|------------------|------------------------------|
| `SugarBean::retrieve()` | `EntityManagerInterface::find()` / Repository |
| `BeanFactory::getBean()` | DI Container with autowiring |
| `DBManager::getConnection()` | Doctrine DBAL / QueryBuilder |
| `sugar_cache_*` | Symfony Cache component |
| `global $db` | `EntityManagerInterface` via DI |
| `global $current_user` | `TokenStorageInterface::getToken()->getUser()` |
| `global $app_strings` | `TranslationServiceInterface` |
| `$sugar_config` | `ParameterBagInterface` |
| vardef arrays | Doctrine Entity attributes |
| `ACLController::checkAccess()` | Symfony Voter system |
| `load_relationship()` | Doctrine eager/lazy loading |
| `get_list()` | Repository with criteria |
| `create_new_list_query()` | QueryBuilder with filters |

---

## Anti-Patterns to Avoid

1. **Direct `DBManager::getConnection()` queries in Controllers** — Use repositories
2. **Global `BeanFactory::getBean()` calls** — Inject services via DI
3. **`sugar_cache_*` in domain services** — Use Symfony Cache component
4. **Global `$db`, `$current_user` throughout** — Use constructor injection
5. **vardef arrays in PHP files** — Use Doctrine Entity attributes
6. **ACL checks in business logic** — Use Symfony Voter annotations
7. **`SugarBean::retrieve()` in repositories** — Use Doctrine QueryBuilder
8. **Load relationships in loops** — Use eager loading or QueryBuilder joins