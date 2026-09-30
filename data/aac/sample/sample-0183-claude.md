# AI-Powered Wellness Coach App - Development Instructions

## Project Overview
Build a mobile wellness app combining AI-powered daily check-ins with habit tracking. Provides personalized wellness insights based on mood, energy, and sleep quality patterns.

## Technology Stack
- **Frontend**: SwiftUI
- **Backend**: Firebase (Auth, Firestore, Cloud Functions)
- **AI**: OpenAI GPT-4-mini, Anthropic Claude API or local Foundation Model (default)
- **Local Storage**: SwiftData
- **Notifications**: Firebase Cloud Messaging
- **State Management**: Combine + SwiftUI <REDACTED_USER>

## Architecture

### Hybrid Clean Architecture + MVVM Approach

Bloom uses a pragmatic hybrid architecture combining Clean Architecture principles with MVVM patterns. This approach balances rapid development (14-day timeline) with maintainability and testability.

**Why This Architecture for Bloom:**
- **Multiple Data Sources**: Clean separation between Firebase, SwiftData, and AI services
- **Complex Business Logic**: Streak calculations, correlation analysis, and offline sync need isolation
- **Testability**: Core wellness logic can be tested independently of UI and frameworks
- **Scalability**: Easy to add premium features, new AI providers, or data export capabilities
- **SwiftUI Native**: MVVM pattern aligns naturally with SwiftUI's declarative approach and <REDACTED_USER> property wrappers

**Key Principles:**
1. **Domain Layer** contains business logic with zero external dependencies (pure Swift)
2. **Data Layer** handles all external I/O (Firebase, SwiftData, network)
3. **Presentation Layer** uses ViewModels (<REDACTED_USER> classes) to access use cases
4. **Dependency Injection** via Swift protocols and property injection keeps layers loosely coupled
5. **Unidirectional Data Flow** through Combine publishers and SwiftUI's <REDACTED_USER> properties

### Folder Structure

```
Bloom/
├── Domain/                          # Business Logic Layer (Framework Independent)
│   ├── Entities/                    # Core business objects
│   │   ├── UserProfile.swift
│   │   ├── DailyCheckIn.swift
│   │   ├── Habit.swift
│   │   └── WellnessGoal.swift
│   ├── UseCases/                    # Business use cases (one per action)
│   │   ├── Auth/
│   │   │   ├── SignInUseCase.swift
│   │   │   ├── SignUpUseCase.swift
│   │   │   └── SignOutUseCase.swift
│   │   ├── CheckIn/
│   │   │   ├── SubmitCheckInUseCase.swift
│   │   │   ├── GetTodayCheckInUseCase.swift
│   │   │   └── GetCheckInHistoryUseCase.swift
│   │   ├── Habits/
│   │   │   ├── CreateHabitUseCase.swift
│   │   │   ├── CompleteHabitUseCase.swift
│   │   │   ├── CalculateStreakUseCase.swift
│   │   │   └── GetHabitCorrelationsUseCase.swift
│   │   ├── Insights/
│   │   │   ├── GenerateAIInsightUseCase.swift
│   │   │   ├── AnalyzeWeeklyPatternsUseCase.swift
│   │   │   └── GetPersonalizedTipsUseCase.swift
│   │   └── Premium/
│   │       ├── StartSubscriptionUseCase.swift
│   │       └── ExportDataUseCase.swift
│   └── Repositories/                # Repository protocols (contracts)
│       ├── AuthRepositoryProtocol.swift
│       ├── CheckInRepositoryProtocol.swift
│       ├── HabitRepositoryProtocol.swift
│       ├── UserRepositoryProtocol.swift
│       └── AIInsightRepositoryProtocol.swift
│
├── Data/                            # Data Layer (External I/O)
│   ├── Repositories/                # Repository implementations
│   │   ├── AuthRepository.swift
│   │   ├── CheckInRepository.swift
│   │   ├── HabitRepository.swift
│   │   ├── UserRepository.swift
│   │   └── AIInsightRepository.swift
│   ├── DataSources/                 # Data source abstractions
│   │   ├── Remote/
│   │   │   ├── FirebaseAuthDataSource.swift
│   │   │   ├── FirestoreDataSource.swift
│   │   │   └── OpenAIDataSource.swift
│   │   └── Local/
│   │       ├── SwiftDataSource.swift
│   │       └── UserDefaultsDataSource.swift
│   ├── Models/                      # DTOs (Data Transfer Objects)
│   │   ├── UserDTO.swift
│   │   ├── CheckInDTO.swift
│   │   └── HabitDTO.swift
│   ├── Mappers/                     # Convert DTOs ↔ Domain entities
│   │   ├── UserMapper.swift
│   │   ├── CheckInMapper.swift
│   │   └── HabitMapper.swift
│   └── Sync/                        # Offline-first sync logic
│       ├── SyncManager.swift
│       └── SyncQueue.swift
│
├── Presentation/                    # Presentation Layer (MVVM)
│   ├── Screens/                     # Screen views
│   │   ├── Auth/
│   │   │   ├── SignInView.swift
│   │   │   ├── SignUpView.swift
│   │   │   └── OnboardingView.swift
│   │   ├── CheckIn/
│   │   │   ├── CheckInView.swift
│   │   │   └── InsightView.swift
│   │   ├── Habits/
│   │   │   ├── HabitsView.swift
│   │   │   └── CreateHabitView.swift
│   │   ├── Progress/
│   │   │   ├── ProgressView.swift
│   │   │   └── AnalyticsView.swift
│   │   ├── Premium/
│   │   │   └── ChatView.swift
│   │   └── Settings/
│   │       └── SettingsView.swift
│   ├── Components/                  # Reusable UI components
│   │   ├── Common/
│   │   │   ├── PrimaryButton.swift
│   │   │   ├── CardView.swift
│   │   │   ├── CustomTextField.swift
│   │   │   └── LoadingSpinner.swift
│   │   ├── CheckIn/
│   │   │   ├── MoodSlider.swift
│   │   │   ├── EnergySlider.swift
│   │   │   └── SleepInput.swift
│   │   ├── Habits/
│   │   │   ├── HabitCard.swift
│   │   │   ├── StreakCounter.swift
│   │   │   └── HabitIconPicker.swift
│   │   └── Charts/
│   │       ├── MoodTrendChart.swift
│   │       ├── HeatMapCalendar.swift
│   │       └── CorrelationGraph.swift
│   ├── ViewModels/                  # Observable ViewModels
│   │   ├── AuthViewModel.swift
│   │   ├── CheckInViewModel.swift
│   │   ├── HabitsViewModel.swift
│   │   ├── InsightsViewModel.swift
│   │   └── ProgressViewModel.swift
│   ├── Navigation/                  # SwiftUI Navigation
│   │   ├── AppCoordinator.swift
│   │   ├── NavigationRouter.swift
│   │   └── Route.swift
│   └── Theme/                       # Design system
│       ├── Colors.swift
│       ├── Typography.swift
│       ├── Spacing.swift
│       └── Animations.swift
│
├── Infrastructure/                  # Framework & External Dependencies
│   ├── DependencyInjection/         # Dependency Injection
│   │   ├── DependencyContainer.swift
│   │   └── Injectable.swift
│   ├── Config/                      # Configuration
│   │   ├── FirebaseConfig.swift
│   │   ├── OpenAIConfig.swift
│   │   └── Environment.swift
│   ├── Services/                    # Platform services
│   │   ├── NotificationService.swift
│   │   ├── AnalyticsService.swift
│   │   └── PurchaseService.swift
│   └── Utils/                       # Shared utilities
│       ├── DateUtils.swift
│       ├── Validation.swift
│       └── Logger.swift
│
└── App/                             # App entry point
    ├── BloomApp.swift               # <REDACTED_USER> App struct
    └── AppState.swift               # Global app state (<REDACTED_USER>)
```

### Layer Responsibilities

#### Domain Layer (`Domain/`)
**Purpose**: Contains all business logic with zero dependencies on frameworks or external libraries.

**Entities** (`Domain/Entities/`): Pure Swift structs representing business concepts:
```swift
// Domain/Entities/DailyCheckIn.swift
struct DailyCheckIn {
    let id: String
    let userId: String
    let timestamp: Date
    let moodScore: Int
    let energyScore: Int
    let sleepHours: Double
    let sleepQuality: Int
    let notes: String?
    var aiInsight: String?
    let isMorning: Bool
}
```

**Use Cases** (`Domain/UseCases/`): Single-responsibility business operations:
```swift
// Domain/UseCases/CheckIn/SubmitCheckInUseCase.swift
final class SubmitCheckInUseCase {
    private let checkInRepo: CheckInRepositoryProtocol
    private let aiRepo: AIInsightRepositoryProtocol
    private let userRepo: UserRepositoryProtocol

    init(
        checkInRepo: CheckInRepositoryProtocol,
        aiRepo: AIInsightRepositoryProtocol,
        userRepo: UserRepositoryProtocol
    ) {
        self.checkInRepo = checkInRepo
        self.aiRepo = aiRepo
        self.userRepo = userRepo
    }

    func execute(checkIn: DailyCheckIn) async throws -> String {
        // 1. Save check-in
        try await checkInRepo.save(checkIn)

        // 2. Generate AI insight
        let insight = try await aiRepo.generateInsight(for: checkIn)
        try await checkInRepo.updateInsight(id: checkIn.id, insight: insight)

        // 3. Update user streak
        let streak = try await calculateStreak(userId: checkIn.userId)
        try await userRepo.updateStreak(userId: checkIn.userId, streak: streak)

        return insight
    }

    private func calculateStreak(userId: String) async throws -> Int {
        // Streak calculation logic
        return 0
    }
}
```

**Repository Protocols** (`Domain/Repositories/`): Contracts that data layer implements:
```swift
// Domain/Repositories/CheckInRepositoryProtocol.swift
protocol CheckInRepositoryProtocol {
    func save(_ checkIn: DailyCheckIn) async throws
    func getById(_ id: String) async throws -> DailyCheckIn?
    func getTodayCheckIn(userId: String) async throws -> DailyCheckIn?
    func getHistory(userId: String, days: Int) async throws -> [DailyCheckIn]
    func updateInsight(id: String, insight: String) async throws
}
```

#### Data Layer (`Data/`)
**Purpose**: Implements data access and manages external I/O operations.

**Repositories** (`Data/Repositories/`): Implement domain repository protocols:
```swift
// Data/Repositories/CheckInRepository.swift
final class CheckInRepository: CheckInRepositoryProtocol {
    private let firestore: FirestoreDataSource
    private let swiftData: SwiftDataSource
    private let mapper: CheckInMapper
    private let syncQueue: SyncQueue

    init(
        firestore: FirestoreDataSource,
        swiftData: SwiftDataSource,
        mapper: CheckInMapper,
        syncQueue: SyncQueue
    ) {
        self.firestore = firestore
        self.swiftData = swiftData
        self.mapper = mapper
        self.syncQueue = syncQueue
    }

    func save(_ checkIn: DailyCheckIn) async throws {
        let dto = mapper.toDTO(checkIn)

        // Save locally first (offline-first)
        try await swiftData.insertCheckIn(dto)

        // Sync to cloud
        do {
            try await firestore.saveCheckIn(dto)
        } catch {
            // Queue for later sync
            try await syncQueue.add(type: "checkIn", data: dto)
        }
    }

    func getTodayCheckIn(userId: String) async throws -> DailyCheckIn? {
        // Try local first
        guard let dto = try await swiftData.getTodayCheckIn(userId: userId) else {
            return nil
        }
        return mapper.toDomain(dto)
    }
}
```

**Data Sources** (`Data/DataSources/`): Platform-specific implementations:
```swift
// Data/DataSources/Remote/FirestoreDataSource.swift
import FirebaseFirestore

final class FirestoreDataSource {
    private let db = Firestore.firestore()

    func saveCheckIn(_ checkIn: CheckInDTO) async throws {
        try await db.collection("checkIns")
            .document(checkIn.id)
            .setData(checkIn.toDictionary())
    }
}

// Data/DataSources/Local/SwiftDataSource.swift
import SwiftData

final class SwiftDataSource {
    private let modelContext: ModelContext

    init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    func insertCheckIn(_ checkIn: CheckInDTO) async throws {
        let model = CheckInModel(from: checkIn)
        modelContext.insert(model)
        try modelContext.save()
    }
}
```

**Mappers** (`Data/Mappers/`): Convert between DTOs and domain entities:
```swift
// Data/Mappers/CheckInMapper.swift
struct CheckInMapper {
    func toDTO(_ entity: DailyCheckIn) -> CheckInDTO {
        CheckInDTO(
            id: entity.id,
            userId: entity.userId,
            timestamp: entity.timestamp.ISO8601Format(),
            moodScore: entity.moodScore,
            energyScore: entity.energyScore,
            sleepHours: entity.sleepHours,
            sleepQuality: entity.sleepQuality,
            notes: entity.notes,
            aiInsight: entity.aiInsight,
            isMorning: entity.isMorning
        )
    }

    func toDomain(_ dto: CheckInDTO) -> DailyCheckIn {
        DailyCheckIn(
            id: dto.id,
            userId: dto.userId,
            timestamp: ISO8601DateFormatter().date(from: dto.timestamp) ?? Date(),
            moodScore: dto.moodScore,
            energyScore: dto.energyScore,
            sleepHours: dto.sleepHours,
            sleepQuality: dto.sleepQuality,
            notes: dto.notes,
            aiInsight: dto.aiInsight,
            isMorning: dto.isMorning
        )
    }
}
```

#### Presentation Layer (`Presentation/`)
**Purpose**: UI components and ViewModels following MVVM pattern.

**ViewModels** (`Presentation/ViewModels/`): Observable classes that bridge UI and use cases:
```swift
// Presentation/ViewModels/CheckInViewModel.swift
import SwiftUI
import Combine

<REDACTED_USER>
final class CheckInViewModel {
    private let submitUseCase: SubmitCheckInUseCase
    private let getTodayUseCase: GetTodayCheckInUseCase

    var isLoading = false
    var todayCheckIn: DailyCheckIn?
    var errorMessage: String?

    var hasCompletedToday: Bool {
        todayCheckIn != nil
    }

    init(
        submitUseCase: SubmitCheckInUseCase,
        getTodayUseCase: GetTodayCheckInUseCase
    ) {
        self.submitUseCase = submitUseCase
        self.getTodayUseCase = getTodayUseCase

        Task {
            await loadTodayCheckIn()
        }
    }

    <REDACTED_USER>
    func loadTodayCheckIn() async {
        do {
            todayCheckIn = try await getTodayUseCase.execute()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    <REDACTED_USER>
    func submitCheckIn(_ data: CheckInFormData) async -> String? {
        isLoading = true
        defer { isLoading = false }

        do {
            let checkIn = data.toDomainModel()
            let insight = try await submitUseCase.execute(checkIn: checkIn)
            todayCheckIn = checkIn
            return insight
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }
}
```

**Views** (`Presentation/Screens/`): SwiftUI views using ViewModels:
```swift
// Presentation/Screens/CheckIn/CheckInView.swift
import SwiftUI

struct CheckInView: View {
    <REDACTED_USER> private var viewModel: CheckInViewModel
    <REDACTED_USER> private var navigateToInsight = false
    <REDACTED_USER> private var generatedInsight: String?

    var body: some View {
        Group {
            if viewModel.hasCompletedToday {
                AlreadyCompletedView()
            } else {
                CheckInForm(
                    isLoading: viewModel.isLoading,
                    onSubmit: handleSubmit
                )
            }
        }
        .navigationDestination(isPresented: $navigateToInsight) {
            if let insight = generatedInsight {
                InsightView(insight: insight)
            }
        }
    }

    private func handleSubmit(_ data: CheckInFormData) {
        Task {
            if let insight = await viewModel.submitCheckIn(data) {
                generatedInsight = insight
                navigateToInsight = true
            }
        }
    }
}
```

#### Infrastructure Layer (`Infrastructure/`)
**Purpose**: Framework configuration, DI container, and platform services.

**Dependency Injection** (`Infrastructure/DependencyInjection/`):
```swift
// Infrastructure/DependencyInjection/DependencyContainer.swift
import Foundation

final class DependencyContainer {
    static let shared = DependencyContainer()

    // Data Sources (Singletons)
    private(set) lazy var firestoreDataSource = FirestoreDataSource()
    private(set) lazy var swiftDataSource: SwiftDataSource = {
        let modelContainer = try! ModelContainer(for: CheckInModel.self, HabitModel.self)
        return SwiftDataSource(modelContext: modelContainer.mainContext)
    }()
    private(set) lazy var openAIDataSource = OpenAIDataSource()

    // Mappers
    private(set) lazy var checkInMapper = CheckInMapper()
    private(set) lazy var habitMapper = HabitMapper()

    // Sync
    private(set) lazy var syncQueue = SyncQueue()

    // Repositories (Singletons)
    private(set) lazy var checkInRepository: CheckInRepositoryProtocol = CheckInRepository(
        firestore: firestoreDataSource,
        swiftData: swiftDataSource,
        mapper: checkInMapper,
        syncQueue: syncQueue
    )

    private(set) lazy var habitRepository: HabitRepositoryProtocol = HabitRepository(
        firestore: firestoreDataSource,
        swiftData: swiftDataSource,
        mapper: habitMapper
    )

    // Use Cases (New instance each time)
    func makeSubmitCheckInUseCase() -> SubmitCheckInUseCase {
        SubmitCheckInUseCase(
            checkInRepo: checkInRepository,
            aiRepo: aiInsightRepository,
            userRepo: userRepository
        )
    }

    func makeCompleteHabitUseCase() -> CompleteHabitUseCase {
        CompleteHabitUseCase(habitRepo: habitRepository)
    }

    private init() {}
}

// Infrastructure/DependencyInjection/Injectable.swift
protocol Injectable {
    static func resolve() -> Self
}

extension SubmitCheckInUseCase: Injectable {
    static func resolve() -> SubmitCheckInUseCase {
        DependencyContainer.shared.makeSubmitCheckInUseCase()
    }
}
```

### Data Flow Example

**User submits a daily check-in:**
1. **UI** (`CheckInView.swift`) → calls `submitCheckIn()` from ViewModel
2. **ViewModel** (`CheckInViewModel.swift`) → calls `SubmitCheckInUseCase.execute()`
3. **Use Case** → orchestrates:
   - `CheckInRepository.save()` → saves to SwiftData + Firestore
   - `AIInsightRepository.generateInsight()` → calls OpenAI API
   - `UserRepository.updateStreak()` → calculates and updates streak
4. **Repository** → uses data sources (SwiftData, Firestore, OpenAI)
5. **<REDACTED_USER> ViewModel** → updates published properties
6. **SwiftUI View** → automatically re-renders with new data

**Key Benefits:**
- Business logic (streak calculation) is in use case, testable without Firebase/SwiftUI
- Swap OpenAI for Claude by changing one data source
- Offline support handled in repository layer
- UI only knows about ViewModels, not data sources
- Native Swift async/await for clean concurrency

## 14-Day Development Timeline

### Phase 1: Foundation (Days 1-3)
**User Authentication:**
- Email/password + Google + Apple Sign-In (Firebase Auth)
- Onboarding flow with wellness goal selection

**Daily Check-In Interface:**
- 3-question survey: mood (1-10), energy (1-10), sleep (hours + quality)
- Optional notes field
- Beautiful minimal SwiftUI interface with animations
- Morning vs evening check-in tracking

**Local Storage:**
- SwiftData models for check-in history
- Offline-first with Firestore sync

### Phase 2: AI Integration (Days 4-6)
**AI Wellness Insights:**
- Daily personalized messages from check-in data
- Weekly pattern analysis and recommendations
- Contextual suggestions based on trends
- System prompt: "You are a supportive wellness coach... provide brief encouraging insight (2-3 sentences) and one actionable tip."

**AI Chat (Premium):**
- Conversational wellness coaching
- Sleep, stress, mood guidance
- Free tier: 5 insights/week, Premium: unlimited

**Cost Management:**
- Use GPT-4-mini (~$0.0001/request)
- Cache common responses
- Rate limiting for free users

### Phase 3: Habit Tracking (Days 7-9)
**Simple Habits:**
- Max 5 active habits (prevents overwhelm)
- Templates: meditation, exercise, water, reading, gratitude
- Custom creation with icon/color picker
- Daily checkboxes + streak counters

**AI Correlation Analysis:**
- "Your mood is 20% higher on days you meditate"
- Visual correlation graphs

**Reminders:**
- Push notifications for check-ins
- Habit reminders with smart timing

### Phase 4: Premium & Visualization (Days 10-12)
**Progress Dashboard:**
- 7-day and 30-day trend charts
- Heat maps and calendar views
- Weekly summary cards

**Premium Implementation:**
- $9.99/month or $79.99/year
- 7-day free trial
- In-app purchase integration
- Features: unlimited AI chat, 10 habits, advanced analytics, data export

### Phase 5: Polish & Launch (Days 13-14)
- UI refinement with smooth animations
- Haptic feedback
- Dark mode
- Onboarding tutorial
- App store assets (screenshots, video, copy)
- Privacy policy

## Core Data Models

**Note**: These are domain entities in `Domain/Entities/`. See the [Architecture](#architecture) section for complete implementation details including DTOs, mappers, and repository protocols.

```swift
// Domain/Entities/UserProfile.swift
struct UserProfile {
    let id: String
    let email: String
    let displayName: String
    let createdAt: Date
    let subscriptionTier: SubscriptionTier
    let wellnessGoals: [String]
    var checkInStreak: Int
}

enum SubscriptionTier: String, Codable {
    case free
    case premium
}

// Domain/Entities/DailyCheckIn.swift
struct DailyCheckIn {
    let id: String
    let userId: String
    let timestamp: Date
    let moodScore: Int       // 1-10
    let energyScore: Int     // 1-10
    let sleepHours: Double
    let sleepQuality: Int    // 1-10
    let notes: String?
    var aiInsight: String?
    let isMorning: Bool
}

// Domain/Entities/Habit.swift
struct Habit {
    let id: String
    let userId: String
    let name: String
    let icon: String
    let color: String
    let createdAt: Date
    var completedDates: [Date]
    var currentStreak: Int
    var longestStreak: Int
    var isActive: Bool
}
```

**SwiftData Models** (in `Data/Models/`):
- Use `<REDACTED_USER>` macro for SwiftData persistence
- Store locally with automatic iCloud sync support

**Firestore Schema** (DTOs in `Data/Models/`):
- Collections: `users/`, `checkIns/`, `habits/`
- Use mappers in `Data/Mappers/` to convert between domain entities and Firestore documents
- Field names use camelCase for Firestore (Swift convention)

## UI/UX Design
**Design System:**
- Built with SwiftUI native components
- Follows iOS Human Interface Guidelines
- Smooth animations using SwiftUI's animation modifiers
- Haptic feedback using UIFeedbackGenerator

**Colors:**
- Primary: Calming teal (#4DB6AC)
- Secondary: Warm coral (#FF8A65)
- Success: Soft green (#81C784)
- Background: Off-white (#FAFAFA) / Dark (#121212)
- Supports iOS Light/Dark mode automatically

**Key Screens:**
1. Home: Today's check-in status, streaks, habit toggles
2. Check-In Flow: Single-screen survey with custom sliders
3. AI Insight: Full-screen shareable card (share sheet integration)
4. Habits: Grid view with completion checkboxes
5. Progress: Charts using Swift Charts framework
6. Chat (Premium): AI conversation with message bubbles
7. Settings: Native iOS Settings-style list

## Monetization

**Free:** Unlimited check-ins, 5 AI insights/week, 3 habits, 7-day history

**Premium ($9.99/mo or $79.99/yr):** Unlimited AI, 10 habits, full history, advanced analytics, export, themes

**Revenue Projections:**
- 1,000 users @ 8% conversion = $3,350/month
- 10,000 users @ 10% conversion = $33,000-40,000/month

## Marketing Strategy
**Pre-launch:** Product Hunt prep, Reddit posts, social media
**Launch:** PH launch, app reviews, demo videos, $100 Meta ads
**Post-launch:** User feedback, build in public, ASO optimization

## Success Metrics
- DAU: 60%+
- Check-in completion: 70%+
- Free to premium: 8-10%
- Day 7 retention: 50%+
- Day 30 retention: 30%+

## App Store Listing
**Title:** "Bloom - AI Wellness Coach"
**Subtitle:** "Daily check-ins, AI insights, habit tracking"
**Keywords:** wellness, mental health, mood tracker, AI coach, habit, meditation, mindfulness, bloom

Start building! Focus on the magical daily check-in experience. 🚀