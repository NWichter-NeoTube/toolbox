import XCTest
@testable import ToolboxApp

// MARK: - Analytics Manager Tests

/// Unit tests for `AnalyticsManager` consent logic and UserDefaults persistence.
///
/// These tests use an isolated `UserDefaults` suite so they never pollute the
/// standard defaults and can run independently of one another.
final class AnalyticsManagerTests: XCTestCase {

    // MARK: - Properties

    private var suiteName: String!
    private var defaults: UserDefaults!
    private var sut: AnalyticsManager!

    // MARK: - Lifecycle

    override func setUp() {
        super.setUp()
        suiteName = "com.toolbox.tests.\(UUID().uuidString)"
        defaults = UserDefaults(suiteName: suiteName)!
        sut = AnalyticsManager(defaults: defaults)
    }

    override func tearDown() {
        sut = nil
        defaults.removePersistentDomain(forName: suiteName)
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    // MARK: - Consent Grant / Revoke

    func testInitialConsentIsFalse() {
        XCTAssertFalse(sut.consentGranted, "Consent must default to false (opted-out).")
    }

    func testGrantConsentUpdatesPublishedProperty() {
        sut.grantConsent()
        XCTAssertTrue(sut.consentGranted)
    }

    func testRevokeConsentUpdatesPublishedProperty() {
        sut.grantConsent()
        sut.revokeConsent()
        XCTAssertFalse(sut.consentGranted)
    }

    // MARK: - UserDefaults Persistence

    func testGrantConsentPersistsToUserDefaults() {
        sut.grantConsent()
        XCTAssertTrue(defaults.bool(forKey: Config.Defaults.analyticsConsent))
    }

    func testRevokeConsentPersistsToUserDefaults() {
        sut.grantConsent()
        sut.revokeConsent()
        XCTAssertFalse(defaults.bool(forKey: Config.Defaults.analyticsConsent))
    }

    func testConsentStateRestoredFromUserDefaults() {
        defaults.set(true, forKey: Config.Defaults.analyticsConsent)

        let restored = AnalyticsManager(defaults: defaults)
        XCTAssertTrue(restored.consentGranted, "Manager should restore consent state from UserDefaults.")
    }

    // MARK: - Event Tracking Guards

    /// Verifies that `trackEvent` silently no-ops when consent is not granted.
    /// (We cannot easily assert PostHog internals, but we can ensure no crash.)
    func testTrackEventWithoutConsentDoesNotCrash() {
        XCTAssertFalse(sut.consentGranted)
        sut.trackEvent(name: "test_event", properties: ["key": "value"])
        // No assertion needed -- reaching this line means no crash.
    }

    func testTrackEventWithConsentDoesNotCrash() {
        sut.grantConsent()
        sut.trackEvent(name: "test_event", properties: ["key": "value"])
    }

    func testIdentifyUserWithoutConsentDoesNotCrash() {
        XCTAssertFalse(sut.consentGranted)
        sut.identifyUser(id: "user-123", properties: ["plan": "pro"])
    }

    func testIdentifyUserWithConsentDoesNotCrash() {
        sut.grantConsent()
        sut.identifyUser(id: "user-123", properties: ["plan": "pro"])
    }

    func testTrackScreenWithoutConsentDoesNotCrash() {
        XCTAssertFalse(sut.consentGranted)
        sut.trackScreen(name: "Home")
    }

    func testTrackScreenWithConsentDoesNotCrash() {
        sut.grantConsent()
        sut.trackScreen(name: "Home")
    }

    // MARK: - Multiple Grant / Revoke Cycles

    func testMultipleConsentCyclesStayConsistent() {
        sut.grantConsent()
        XCTAssertTrue(sut.consentGranted)

        sut.revokeConsent()
        XCTAssertFalse(sut.consentGranted)

        sut.grantConsent()
        XCTAssertTrue(sut.consentGranted)

        XCTAssertTrue(defaults.bool(forKey: Config.Defaults.analyticsConsent))
    }
}
