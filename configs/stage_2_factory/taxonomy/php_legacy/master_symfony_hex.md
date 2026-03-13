# Symfony Hexagonal Architecture Doctrine

This document defines the target architecture for modernizing legacy PHP applications to Symfony with hexagonal (ports & adapters) architecture.

## Overview

Hexagonal Architecture (also known as Ports and Adapters) separates an application into three main layers:

1. **Domain Layer** (Core) — Business logic, entities, value objects
2. **Application Layer** — Use cases, application services, DTOs
3. **Infrastructure Layer** — Adapters, repositories, external services

The key principle is that **the core domain has no dependencies on external frameworks** — all interactions happen through ports (interfaces).

---

## Ports (Domain Interfaces)

Ports are interfaces that define contracts between the domain and the outside world. They are the **abstractions** that the domain depends on.

### Types of Ports

#### Driving Ports (Primary/Input)
- **Use Case Interfaces**: Define what the application can do
- **Command Handlers**: Handle user commands (CQRS pattern)
- **Query Handlers**: Handle data retrieval queries

#### Driven Ports (Secondary/Output)
- **Repository Interfaces**: Define data access contracts
- **Service Interfaces**: Define external service contracts (email, payment, etc.)
- **Event Publisher Interfaces**: Define event dispatch contracts

### Port Naming Conventions

```php
// Driving Ports
interface CustomerQueryInterface {
    public function findById(int $id): ?CustomerDTO;
    public function findByEmail(string $email): array;
}

interface OrderCommandInterface {
    public function createOrder(CreateOrderCommand $command): OrderDTO;
    public function cancelOrder(int $orderId): void;
}

// Driven Ports
interface CustomerRepositoryInterface {
    public function save(Customer $customer): void;
    public function findById(int $id): ?Customer;
    public function delete(int $id): void;
}

interface MailerInterface {
    public function send(Message $message): void;
    public function sendTemplate(string $template, array $context): void;
}

interface EventDispatcherInterface {
    public function dispatch(object $event): void;
    public function addListener(string $eventName, callable $listener): void;
}
```

---

## Adapters (Infrastructure Implementations)

Adapters are concrete implementations of ports. They connect the domain to external systems (databases, HTTP clients, message queues, etc.).

### Types of Adapters

#### Inbound Adapters (Driving)
- **Controllers**: Symfony controllers that handle HTTP requests
- **Console Commands**: CLI command handlers
- **Message Handlers**: Handle messages from a queue

#### Outbound Adapters (Driven)
- **Doctrine Repositories**: Database persistence
- **HTTP Clients**: External API calls
- **Mail Adapters**: Email sending (SwiftMailer, Symfony Mailer)
- **Cache Adapters**: Redis, Memcached

### Adapter Implementation Example

```php
// Driven Port (Interface in Domain)
interface CustomerRepositoryInterface {
    public function findById(int $id): ?Customer;
    public function save(Customer $customer): void;
}

// Outbound Adapter (Infrastructure)
class DoctrineCustomerRepository implements CustomerRepositoryInterface
{
    private EntityManagerInterface $em;

    public function __construct(EntityManagerInterface $em)
    {
        $this->em = $em;
    }

    public function findById(int $id): ?Customer
    {
        return $this->em->find(Customer::class, $id);
    }

    public function save(Customer $customer): void
    {
        $this->em->persist($customer);
        $this->em->flush();
    }
}
```

---

## DTOs (Data Transfer Objects)

DTOs are simple objects that carry data between layers. They should be **immutable** and contain no business logic.

### DTO Principles

1. **Immutable**: Use `readonly` properties or frozen dataclasses
2. **Flat Structure**: Avoid nested objects unless necessary
3. **Serialization Aware**: Implement `JsonSerializable` if needed
4. **Validation**: Use Symfony Validator or PHP 8 attributes

### DTO Example

```php
// Request DTO
readonly class CreateCustomerRequest
{
    public function __construct(
        public string $email,
        public string $name,
        public ?string $phone = null
    ) {
        // Automatic validation can be added via attributes
    }
}

// Response DTO
readonly class CustomerResponse
{
    public function __construct(
        public int $id,
        public string $email,
        public string $name,
        public ?string $phone,
        public DateTimeImmutable $createdAt
    ) {}

    public static function fromEntity(Customer $customer): self
    {
        return new self(
            id: $customer->getId(),
            email: $customer->getEmail(),
            name: $customer->getName(),
            phone: $customer->getPhone(),
            createdAt: $customer->getCreatedAt()
        );
    }
}
```

---

## Doctrine ORM as Persistence

Doctrine is the standard ORM for Symfony applications. It provides object-relational mapping with a powerful QueryBuilder and DQL.

### Entity Configuration

```php
#[ORM\Entity]
#[ORM\Table(name: 'customers')]
class Customer
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\Column(type: 'string', length: 255, unique: true)]
    private string $email;

    #[ORM\Column(type: 'string', length: 255)]
    private string $name;

    #[ORM\OneToMany(mappedBy: 'customer', targetEntity: Order::class)]
    private Collection $orders;

    public function __construct(string $email, string $name)
    {
        $this->email = $email;
        $this->name = $name;
        $this->orders = new ArrayCollection();
    }

    // Getters and business methods only - no setters for core fields
}
```

### Repository Pattern with Doctrine

```php
class CustomerRepository implements CustomerRepositoryInterface
{
    public function __construct(
        private EntityManagerInterface $em
    ) {}

    private function getRepository(): EntityRepository
    {
        return $this->em->getRepository(Customer::class);
    }

    public function findById(int $id): ?Customer
    {
        return $this->getRepository()->find($id);
    }

    public function findByEmail(string $email): ?Customer
    {
        return $this->getRepository()->findOneBy(['email' => $email]);
    }

    public function findAllActive(): array
    {
        return $this->getRepository()->findBy(['isActive' => true]);
    }

    public function save(Customer $customer): void
    {
        $this->em->persist($customer);
        $this->em->flush();
    }
}
```

### QueryBuilder Usage

```php
class OrderRepository implements OrderRepositoryInterface
{
    public function findRecentOrdersByCustomer(int $customerId, int $limit = 10): array
    {
        return $this->em->createQueryBuilder()
            ->select('o')
            ->from(Order::class, 'o')
            ->where('o.customer = :customerId')
            ->andWhere('o.status != :status')
            ->setParameter('customerId', $customerId)
            ->setParameter('status', OrderStatus::CANCELLED)
            ->orderBy('o.createdAt', 'DESC')
            ->setMaxResults($limit)
            ->getQuery()
            ->getResult();
    }
}
```

---

## Symfony DI Container

The Dependency Injection Container is the heart of a Symfony application. It manages service instantiation and injection.

### Service Definition

```yaml
# config/services.yaml
services:
    _defaults:
        autowire: true
        autoconfigure: true
        public: false

    App\Domain\Customer\CustomerRepositoryInterface:
        '@App\Infrastructure\Persistence\DoctrineCustomerRepository'

    App\Application\Customer\CreateCustomerHandler:
        arguments:
            $repository: '@App\Domain\Customer\CustomerRepositoryInterface'
```

### Dependency Injection Patterns

#### Constructor Injection (Preferred)

```php
class CreateCustomerHandler
{
    public function __construct(
        private CustomerRepositoryInterface $repository,
        private EventDispatcherInterface $dispatcher,
        private LoggerInterface $logger
    ) {}

    public function handle(CreateCustomerCommand $command): Customer
    {
        $customer = new Customer($command->email, $command->name);
        $this->repository->save($customer);
        $this->dispatcher->dispatch(new CustomerCreatedEvent($customer));
        $this->logger->info("Customer created: {$customer->getId()}");
        return $customer;
    }
}
```

#### Interface Injection

```php
interface LoggerAwareInterface
{
    public function setLogger(LoggerInterface $logger);
}

class SomeService implements LoggerAwareInterface
{
    private ?LoggerInterface $logger = null;

    public function setLogger(LoggerInterface $logger): void
    {
        $this->logger = $logger;
    }
}
```

### Service Tags

```php
// Making a service usable as a command handler
#[AsMessageHandler(handle: CreateCustomerCommand::class)]
class CreateCustomerHandler
{
    // ...
}
```

---

## Event Dispatcher as Event Bus

Symfony's EventDispatcher (or Symfony Messenger for async) allows for loose coupling through events.

### Event Definition

```php
class CustomerCreatedEvent
{
    public function __construct(
        public readonly Customer $customer,
        public readonly DateTimeImmutable $occurredAt = new DateTimeImmutable()
    ) {}
}
```

### Event Listener

```php
class SendWelcomeEmailListener
{
    public function __construct(
        private MailerInterface $mailer,
        private TemplateRendererInterface $renderer
    ) {}

    public function onCustomerCreated(CustomerCreatedEvent $event): void
    {
        $html = $this->renderer->render('emails/welcome.html.twig', [
            'customer' => $event->customer
        ]);

        $this->mailer->send((new Email())
            ->to($event->customer->getEmail())
            ->subject('Welcome!')
            ->html($html));
    }
}
```

### Event Subscriber

```php
class CustomerEventSubscriber implements EventSubscriberInterface
{
    public static function getSubscribedEvents(): array
    {
        return [
            CustomerCreatedEvent::class => 'onCustomerCreated',
            CustomerUpdatedEvent::class => 'onCustomerUpdated',
            CustomerDeletedEvent::class => 'onCustomerDeleted',
        ];
    }

    public function onCustomerCreated(CustomerCreatedEvent $event): void
    {
        // Handle event
    }
}
```

---

## Hexagonal Layer Rules

### Layer Responsibilities

| Layer | Responsibility | Dependencies |
|-------|---------------|--------------|
| **Domain** | Business logic, entities, value objects, domain events | None (pure PHP) |
| **Application** | Use cases, DTOs, orchestration | Domain interfaces |
| **Infrastructure** | Adapters, repositories, framework code | Domain interfaces, Symfony |
| **Presentation** | Controllers, CLI, templates | Application services |

### Dependency Rule

> **Inner layers never depend on outer layers.**

```
┌─────────────────────────────────────────────┐
│            Presentation Layer              │
│         (Controllers, Commands)            │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────▼───────────────────────┐
│            Application Layer               │
│    (Use Cases, Handlers, DTOs, Services)   │
└─────────────────────┬───────────────────────┘
                      │ (depends on interfaces)
┌─────────────────────▼───────────────────────┐
│              Domain Layer                  │
│   (Entities, Value Objects, Domain Events,  │
│    Repository Interfaces, Service Interfaces)│
└─────────────────────────────────────────────┘
                      ▲
                      │ (implements interfaces)
┌─────────────────────┴───────────────────────┐
│           Infrastructure Layer             │
│  (Doctrine Repos, HTTP Clients, Mailers)   │
└─────────────────────────────────────────────┘
```

### Legacy PHP → Symfony Mapping

| Legacy PHP Pattern | Symfony Hexagonal Equivalent |
|-------------------|------------------------------|
| `global $db` | `EntityManagerInterface` injected via constructor |
| `tep_db_query()` | `DoctrineRepositoryInterface` with QueryBuilder |
| `$_SESSION['cart']` | `SessionInterface` injected via constructor |
| `global $customer_id` | `UserInterface` / `TokenStorage` from security context |
| `include('file.php')` | Service autowiring / Dependency Injection |
| `define('CONSTANT', ...)` | `.env` parameters / Kernel parameters |
| `mysql_query($sql . $id)` | Doctrine QueryBuilder with parameter binding |
| `function tep_xxx()` | Domain Service / Use Case Handler |
| `switch($action)` case blocks | Command Handlers / Enum-based routing |
| `eval($code)` | Expression Language (controlled) |
| `include($dynamic)` | Service container get() with validation |
| `$_GET['id']` without sanitization | `Request` object with validation (Symfony Validator) |

### Anti-Patterns to Avoid

1. **Entity Manager in Controllers** — Inject repositories, not EM
2. **Business Logic in Entities** — Keep entities thin, use domain services
3. **Direct SQL Queries** — Use Doctrine QueryBuilder or DQL
4. **Global State** — Inject everything via constructor
5. **Twig in Domain** — Separate presentation from business logic
6. **耦合到 Symfony** — Domain should be framework-agnostic

---

## Summary

When modernizing legacy PHP to Symfony hexagonal:

1. **Define Ports First**: Create interfaces for all external dependencies
2. **Implement Adapters**: Build concrete implementations for Doctrine, Mailer, etc.
3. **Use DTOs**: Transfer data between layers with immutable objects
4. **Inject Dependencies**: Everything comes through constructor injection
5. **Dispatch Events**: Decouple operations through event listeners
6. **Keep Domain Pure**: The core should have no Symfony dependencies

This architecture ensures testability, maintainability, and long-term evolvability of your PHP application.
