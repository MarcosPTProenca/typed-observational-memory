# Repository Guidelines

## Project Structure & Module Organization
Work under `src/main/java` for production code and `src/test/java` for demos and baseline assertions. Group each virtual-thread scenario in its own package (for example, `com.example.virtualthreads.scheduling`). Keep helper scripts in `scripts/` and background notes or UML sketches inside `docs/` so the project root remains minimal and newcomers can see the examples instantly. I use gradle as build tool and write gradle files with Kotlin.

## Experiment Workflow
Start new explorations from a small `Main` class that prints thread names and timing details. Capture interesting scheduler behavior with lightweight logging before introducing frameworks. When experimenting with structured concurrency, save intermediate experiments under `sandbox/` and move polished versions into `src/main/java` once the API shape is stable. Document any JVM flags you toggled in a short README snippet within the package.

## Build, Test, and Development Commands
Standardize on Java 21. Compile and run samples with `./mvnw compile exec:java -Dexec.mainClass=com.example.virtualthreads.Main`; Gradle users can mirror this via `./gradlew run`. For single-file experiments, `java --enable-preview --source 21 path/to/Class.java` offers a fast feedback loop. Refresh dependency trees using `./mvnw dependency:tree` or `./gradlew dependencies` whenever you add new libraries, keeping the demo self-explanatory.

## Coding Style & Naming Conventions
Follow conventional Java formatting: four-space indentation, braces on the same line, camelCase for methods, and UpperCamelCase for classes. Name demos after the behavior they illustrate (`StructuredConcurrencyDemo`, `PinnedThreadExample`). Keep methods focused on illustrating one idea; prefer small helper methods over long procedural blocks. Run `./mvnw spotless:apply` (or `./gradlew spotlessApply`) before publishing updates so examples stay consistent.

## Virtual Thread Notes & References
Review Oracle’s Java 21 virtual thread guide for terminology and the lifecycle of virtual vs. platform threads. Highlight any deviations—custom schedulers, executor tweaks, preview APIs—in code comments so reviewers understand why the sample differs from the reference design. Link supporting articles or profiler captures inside the relevant package README for quick cross-reference.