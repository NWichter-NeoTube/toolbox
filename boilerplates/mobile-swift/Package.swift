// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "ToolboxApp",
    platforms: [
        .iOS(.v16),
    ],
    products: [
        .library(
            name: "ToolboxApp",
            targets: ["ToolboxApp"]
        ),
    ],
    dependencies: [
        .package(
            url: "https://github.com/PostHog/posthog-ios.git",
            from: "3.0.0"
        ),
        .package(
            url: "https://github.com/getsentry/sentry-cocoa.git",
            from: "8.0.0"
        ),
        .package(
            url: "https://github.com/Unleash/unleash-proxy-client-swift.git",
            from: "1.0.0"
        ),
    ],
    targets: [
        .target(
            name: "ToolboxApp",
            dependencies: [
                .product(name: "PostHog", package: "posthog-ios"),
                .product(name: "Sentry", package: "sentry-cocoa"),
                .product(name: "UnleashProxyClientSwift", package: "unleash-proxy-client-swift"),
            ],
            path: "Sources"
        ),
        .testTarget(
            name: "ToolboxAppTests",
            dependencies: ["ToolboxApp"],
            path: "Tests"
        ),
    ]
)
