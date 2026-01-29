---
name: swift
description: "Swift/iOS development patterns. Read before creating SwiftUI views, models, or networking code."
---

# Swift/iOS Skill

> Read this before creating SwiftUI views, data models, or iOS app features.

## Project Structure

```
App/
├── App.swift                 # @main entry point
├── ContentView.swift         # Root view
├── Models/
│   ├── User.swift
│   └── DataModels.swift
├── Views/
│   ├── Components/           # Reusable UI components
│   ├── Screens/              # Full screen views
│   └── Modifiers/            # Custom view modifiers
├── ViewModels/               # ObservableObject classes
├── Services/
│   ├── APIClient.swift       # Network layer
│   ├── AuthService.swift
│   └── StorageService.swift
├── Utilities/
│   └── Extensions/
├── Resources/
│   ├── Assets.xcassets
│   └── Localizable.strings
└── Preview Content/
```

## SwiftUI Patterns

### Basic View Structure

```swift
import SwiftUI

struct TaskListView: View {
    @StateObject private var viewModel = TaskListViewModel()
    @State private var showingAddTask = false

    var body: some View {
        NavigationStack {
            List {
                ForEach(viewModel.tasks) { task in
                    TaskRowView(task: task)
                }
                .onDelete(perform: viewModel.deleteTasks)
            }
            .navigationTitle("Tasks")
            .toolbar {
                Button("Add", systemImage: "plus") {
                    showingAddTask = true
                }
            }
            .sheet(isPresented: $showingAddTask) {
                AddTaskView(onSave: viewModel.addTask)
            }
            .task {
                await viewModel.loadTasks()
            }
        }
    }
}

#Preview {
    TaskListView()
}
```

### ViewModel Pattern

```swift
import Foundation
import Observation

@Observable
final class TaskListViewModel {
    private(set) var tasks: [Task] = []
    private(set) var isLoading = false
    private(set) var error: Error?

    private let apiClient: APIClient

    init(apiClient: APIClient = .shared) {
        self.apiClient = apiClient
    }

    func loadTasks() async {
        isLoading = true
        defer { isLoading = false }

        do {
            tasks = try await apiClient.fetch("/tasks")
        } catch {
            self.error = error
        }
    }

    func addTask(_ task: Task) {
        tasks.append(task)
    }

    func deleteTasks(at offsets: IndexSet) {
        tasks.remove(atOffsets: offsets)
    }
}
```

### Reusable Components

```swift
struct LoadingButton: View {
    let title: String
    let isLoading: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if isLoading {
                    ProgressView()
                        .tint(.white)
                }
                Text(title)
            }
            .frame(maxWidth: .infinity)
        }
        .buttonStyle(.borderedProminent)
        .disabled(isLoading)
    }
}

// Usage
LoadingButton(
    title: "Save",
    isLoading: viewModel.isSaving
) {
    Task { await viewModel.save() }
}
```

## Data Models

### Codable Models

```swift
struct Task: Identifiable, Codable, Hashable {
    let id: UUID
    var title: String
    var isCompleted: Bool
    var dueDate: Date?
    var priority: Priority

    enum Priority: String, Codable, CaseIterable {
        case low, medium, high
    }
}

// With custom coding keys
struct User: Codable {
    let id: UUID
    let email: String
    let displayName: String
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case email
        case displayName = "display_name"
        case createdAt = "created_at"
    }
}
```

### SwiftData Models

```swift
import SwiftData

@Model
final class Task {
    var id: UUID
    var title: String
    var isCompleted: Bool
    var dueDate: Date?
    @Relationship(deleteRule: .cascade) var subtasks: [Subtask]

    init(title: String, dueDate: Date? = nil) {
        self.id = UUID()
        self.title = title
        self.isCompleted = false
        self.dueDate = dueDate
        self.subtasks = []
    }
}
```

## Networking

### API Client

```swift
import Foundation

actor APIClient {
    static let shared = APIClient()

    private let baseURL = URL(string: "https://api.example.com")!
    private let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }()

    private var authToken: String?

    func setAuthToken(_ token: String?) {
        self.authToken = token
    }

    func fetch<T: Decodable>(_ path: String) async throws -> T {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = "GET"

        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard 200..<300 ~= httpResponse.statusCode else {
            throw APIError.httpError(statusCode: httpResponse.statusCode)
        }

        return try decoder.decode(T.self, from: data)
    }

    func post<T: Encodable, R: Decodable>(_ path: String, body: T) async throws -> R {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)

        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, _) = try await URLSession.shared.data(for: request)
        return try decoder.decode(R.self, from: data)
    }
}

enum APIError: Error, LocalizedError {
    case invalidResponse
    case httpError(statusCode: Int)
    case decodingError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid server response"
        case .httpError(let code):
            return "Server error: \(code)"
        case .decodingError(let error):
            return "Data error: \(error.localizedDescription)"
        }
    }
}
```

## State Management

### Property Wrappers

```swift
// @State - Simple view-local state
@State private var isExpanded = false

// @Binding - Two-way binding from parent
@Binding var selectedDate: Date

// @StateObject - ViewModel owned by this view
@StateObject private var viewModel = MyViewModel()

// @ObservedObject - ViewModel passed from parent
@ObservedObject var viewModel: MyViewModel

// @EnvironmentObject - Shared across view hierarchy
@EnvironmentObject var authManager: AuthManager

// @Environment - System-provided values
@Environment(\.dismiss) private var dismiss
@Environment(\.colorScheme) private var colorScheme
```

### Environment Setup

```swift
// App.swift
@main
struct MyApp: App {
    @StateObject private var authManager = AuthManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authManager)
        }
        .modelContainer(for: [Task.self])
    }
}
```

## Navigation

### NavigationStack

```swift
struct ContentView: View {
    @State private var path = NavigationPath()

    var body: some View {
        NavigationStack(path: $path) {
            TaskListView(path: $path)
                .navigationDestination(for: Task.self) { task in
                    TaskDetailView(task: task)
                }
                .navigationDestination(for: Route.self) { route in
                    switch route {
                    case .settings:
                        SettingsView()
                    case .profile:
                        ProfileView()
                    }
                }
        }
    }
}

enum Route: Hashable {
    case settings
    case profile
}
```

## Error Handling

```swift
struct ContentView: View {
    @State private var error: Error?
    @State private var showingError = false

    var body: some View {
        TaskListView()
            .alert("Error", isPresented: $showingError, presenting: error) { _ in
                Button("OK", role: .cancel) { }
            } message: { error in
                Text(error.localizedDescription)
            }
    }

    func handleError(_ error: Error) {
        self.error = error
        self.showingError = true
    }
}
```

## Testing

### Unit Tests

```swift
import XCTest
@testable import MyApp

final class TaskListViewModelTests: XCTestCase {
    var sut: TaskListViewModel!
    var mockAPIClient: MockAPIClient!

    override func setUp() {
        super.setUp()
        mockAPIClient = MockAPIClient()
        sut = TaskListViewModel(apiClient: mockAPIClient)
    }

    func testLoadTasksSuccess() async {
        // Given
        let expectedTasks = [Task(title: "Test")]
        mockAPIClient.mockResponse = expectedTasks

        // When
        await sut.loadTasks()

        // Then
        XCTAssertEqual(sut.tasks.count, 1)
        XCTAssertEqual(sut.tasks.first?.title, "Test")
        XCTAssertNil(sut.error)
    }

    func testLoadTasksFailure() async {
        // Given
        mockAPIClient.mockError = APIError.invalidResponse

        // When
        await sut.loadTasks()

        // Then
        XCTAssertTrue(sut.tasks.isEmpty)
        XCTAssertNotNil(sut.error)
    }
}
```

### UI Tests

```swift
import XCTest

final class TaskListUITests: XCTestCase {
    let app = XCUIApplication()

    override func setUp() {
        continueAfterFailure = false
        app.launch()
    }

    func testAddTask() {
        app.buttons["Add"].tap()

        let textField = app.textFields["Task title"]
        textField.tap()
        textField.typeText("New Task")

        app.buttons["Save"].tap()

        XCTAssertTrue(app.staticTexts["New Task"].exists)
    }
}
```

## Common Gotchas

1. **Main Actor** - UI updates must be on main thread: `@MainActor` or `await MainActor.run { }`
2. **Weak self** - Use `[weak self]` in closures to avoid retain cycles
3. **Task cancellation** - Handle `Task.isCancelled` in long operations
4. **Preview crashes** - Use `#if DEBUG` and mock data for previews
5. **Keychain** - Use Keychain for sensitive data, not UserDefaults

## Useful Commands

```bash
# Build
xcodebuild -scheme MyApp -destination 'platform=iOS Simulator,name=iPhone 15'

# Test
xcodebuild test -scheme MyApp -destination 'platform=iOS Simulator,name=iPhone 15'

# Archive
xcodebuild archive -scheme MyApp -archivePath ./build/MyApp.xcarchive

# SwiftLint
swiftlint lint --strict

# Swift Format
swift-format format -i -r Sources/
```
