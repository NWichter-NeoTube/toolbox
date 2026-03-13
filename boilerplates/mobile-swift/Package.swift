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
            url: "https://github.com/getsentry/sentry-cocoa.git",
            from: "8.0.0"
        ),
    ],
    targets: [
        .target(
            name: "ToolboxApp",
            dependencies: [
                .product(name: "Sentry", package: "sentry-cocoa"),
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
