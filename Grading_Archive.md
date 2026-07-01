

## REVIEW SESSION: 2026-07-01
## Concept: GPU Memory Hierarchy & Latency Optimization

<!-- PAGE_ID: RETRIEVAL -->

<!-- CONCEPT_NAME: GPU Memory Hierarchy & Latency Optimization -->

<!-- REF_ANSWER: Kernel arguments reside in global memory, which incurs 400-800 clock cycles of latency per access. When threads repeatedly access these arguments, each access stalls the thread pipeline. The optimization strategy is to load kernel arguments into registers or shared memory at the beginning of the kernel execution. If the argument is used by all threads in a block, loading it into shared memory (via a single coalesced global read) allows subsequent accesses to complete in ~20-30 cycles. If the argument is thread-specific, storing it in a register eliminates latency after the initial load. This transforms O(n) global memory accesses into O(1) fast accesses. -->

**Q:** Explain why accessing kernel arguments directly from global memory within a kernel can become a performance bottleneck, and describe a practical optimization strategy to mitigate this issue.
**Answer:** reads and writes to global memory take a LOT of clock cycles and can decrease occupancy and therefore GPU performance. A practical optimization is tiling- caching args in some more local memory source prevents latency costs of reading and writing to variables.
<!-- GRADED_ON: 2026-07-01 -->
<!-- ASSIGNED_SCORE: 3 -->
**System Feedback:** *The student correctly identifies that global memory access is expensive and proposes caching as a mitigation strategy, but fails to specify concrete mechanisms (registers vs. shared memory), omits critical latency numbers (400-800 vs. 20-30 cycles), and conflates occupancy with latency—the core issue is access latency, not occupancy reduction.*

---
<!-- PAGE_ID: RETRIEVAL -->

<!-- CONCEPT_NAME: GPU Memory Hierarchy & Latency Optimization -->

<!-- REF_ANSWER: When register usage exceeds the per-thread limit, excess values spill to local memory, which is actually a region of global memory. These spilled registers incur 400-800 cycle latencies for each read/write, causing dramatic performance loss. This differs fundamentally from CPUs: CPU compilers also spill to stack memory, but the CPU's automatic L1/L2 cache hierarchy typically keeps frequently-accessed spilled data in fast cache (10-100 cycles). GPUs lack this automatic caching for local memory, so spills directly access global memory at full latency. The solution is explicit register optimization: reduce per-thread working set, use shared memory for temporary storage, or restructure algorithms to fit within register limits. -->

**Q:** A student observes severe performance degradation in their kernel when register usage exceeds the per-thread limit. Identify the underlying mechanism causing this degradation and explain how it differs from the behavior on a CPU with automatic caching.
**Answer:** This may mean that there are too many threads per kernel. Or more aptly, too many threads per block. This reduces the register size on each block (as the total register spice is fixed per block). When registers are overridden, the GPU must move to memory sources that are farther away from cores. I'm not sure how a CPUs automatic cacheing helps here.
<!-- GRADED_ON: 2026-07-01 -->
<!-- ASSIGNED_SCORE: 2 -->
**System Feedback:** *The student correctly identifies that exceeding register limits forces spills to slower memory, but fundamentally misunderstands the mechanism: register allocation is per-thread (not per-block), spills go to global memory with 400-800 cycle latencies (not just "farther away"), and crucially misses the critical distinction that CPUs' automatic L1/L2 caches mitigate spill costs while GPUs lack this automatic caching layer—making the comparison to CPU behavior incomplete and the explanation mechanically imprecise.*

---
<!-- PAGE_ID: RETRIEVAL -->

<!-- CONCEPT_NAME: GPU Memory Hierarchy & Latency Optimization -->

<!-- REF_ANSWER: In tiled matrix multiplication, each thread block loads a tile of the input matrices from global memory into shared memory (a single coalesced operation). Threads then perform computations using this shared data. The __syncthreads() barrier ensures all threads in the block have completed their loads before any thread begins reading from shared memory, preventing race conditions. Subsequent accesses to shared memory complete in ~20-30 cycles instead of 400-800 cycles for global memory. By reusing each loaded tile across multiple arithmetic operations (e.g., computing multiple output elements), the amortized latency per operation decreases significantly. For example, loading a 32×32 tile once and reusing it 32 times reduces effective latency by ~32×, enabling much higher arithmetic intensity and better GPU utilization. -->

**Q:** In a tiling strategy for matrix multiplication, explain how __syncthreads() enables safe data reuse from shared memory and why this approach reduces effective memory latency compared to repeated global memory access.
**Answer:** Sync threads ensures that all threads will perform a memory read at the same time, which ensures that one large memory read can be performed instead of many more.
<!-- GRADED_ON: 2026-07-01 -->
<!-- ASSIGNED_SCORE: 2 -->
**System Feedback:** *The student conflates __syncthreads() with memory coalescing and misses the critical insight that the barrier prevents race conditions during *reads* from shared memory after loads complete, and fails entirely to explain how data *reuse* across multiple operations reduces effective latency—the core mechanism of tiling.*

---
## Concept: Least Squares Problem Formulation & Overdetermined Systems

<!-- PAGE_ID: RETRIEVAL -->

<!-- CONCEPT_NAME: Least Squares Problem Formulation & Overdetermined Systems -->

<!-- REF_ANSWER: The normal equations arise from setting the gradient of the cost function to zero. Taking the derivative: ∇J(x) = 2A^T(Ax - b) = 0, which simplifies to A^T A x = A^T b. The residual r = A^T(Ax - b) is the gradient vector itself (up to a scalar factor of 2). Geometrically, it represents the direction of steepest ascent in the cost function; at the optimal solution, this gradient is zero, meaning the estimate lies in the null space of A^T, which is equivalent to saying the error vector (Ax - b) is orthogonal to all columns of A. This orthogonality condition ensures the solution minimizes the Euclidean norm of the residual. -->

**Q:** In a least squares problem, explain why the normal equations A^T A x = A^T b emerge as the optimality condition. What mathematical operation on the cost function J(x) = ||Ax - b||^2 produces the residual vector r = A^T(Ax - b), and what does this residual represent geometrically?
**Answer:** This emerges out of the derivative of the cost function and setting it equal to zero.
<!-- GRADED_ON: 2026-07-01 -->
<!-- ASSIGNED_SCORE: 2 -->
**System Feedback:** *While the student correctly identifies that the normal equations emerge from taking the derivative and setting it to zero, the answer lacks the explicit mathematical derivation (∇J(x) = 2A^T(Ax - b) = 0), fails to explain what the residual vector represents, and completely omits the critical geometric interpretation of orthogonality between the error and the column space of A.*

---
<!-- PAGE_ID: RETRIEVAL -->

<!-- CONCEPT_NAME: Least Squares Problem Formulation & Overdetermined Systems -->

<!-- REF_ANSWER: A^T A is symmetric because (A^T A)^T = A^T(A^T)^T = A^T A. It is positive semidefinite because for any vector x, the quadratic form x^T(A^T A)x = (Ax)^T(Ax) = ||Ax||^2 ≥ 0. Positive semidefiniteness guarantees that the normal equations A^T A x = A^T b are theoretically solvable in the least squares sense. However, if A^T A is only positive semidefinite (not positive definite), it may be singular when A is rank-deficient, meaning the columns of A are linearly dependent. In such cases, the solution is not unique; infinitely many solutions exist that achieve the same minimum residual norm. For full-column-rank A, A^T A is positive definite and invertible, yielding the unique solution x = (A^T A)^{-1} A^T b. -->

**Q:** Why is the matrix A^T A guaranteed to be symmetric and positive semidefinite in the context of least squares problems, and what implication does positive semidefiniteness have for the solvability of the normal equations?
**Answer:** I do not know.
<!-- GRADED_ON: 2026-07-01 -->
<!-- ASSIGNED_SCORE: 1 -->
**System Feedback:** *The student provided no substantive answer; a complete response requires demonstrating the symmetry proof via transpose properties, deriving positive semidefiniteness from the quadratic form ||Ax||² ≥ 0, and explaining how rank-deficiency leads to non-uniqueness versus full-column-rank yielding the unique solution x = (A^T A)^{-1} A^T b.*

---
<!-- PAGE_ID: RETRIEVAL -->

<!-- CONCEPT_NAME: Least Squares Problem Formulation & Overdetermined Systems -->

<!-- REF_ANSWER: An overdetermined system has more constraints (equations) than degrees of freedom (unknowns). For an exact solution to exist, b must lie in the column space of A, denoted col(A). Since m > n, the column space is a lower-dimensional subspace of ℝ^m, and b generically does not lie in it. The least squares solution x* minimizes ||Ax - b||^2 by finding the point Ax* in col(A) that is closest to b in the Euclidean sense. Mathematically, Ax* is the orthogonal projection of b onto col(A), and the residual vector (b - Ax*) is orthogonal to col(A). This is equivalent to requiring A^T(Ax* - b) = 0, which is precisely the normal equations. The residual norm ||b - Ax*|| represents the irreducible error due to the inconsistency of the overdetermined system. -->

**Q:** Consider an overdetermined system with m equations and n unknowns where m > n. Explain why no exact solution to Ax = b exists in general, and describe how the least squares solution x* relates to the column space of A and the projection of b onto that space.
**Answer:** Because there are more equations than there are parameters.
<!-- GRADED_ON: 2026-07-01 -->
<!-- ASSIGNED_SCORE: 1 -->
**System Feedback:** *The student's answer merely restates the definition of an overdetermined system without addressing the core conceptual question: why b generically does not lie in col(A), how the least squares solution relates to orthogonal projection onto col(A), or the role of the normal equations in minimizing the residual.*

---
## Concept: REST Architecture & Its Purpose

<!-- PAGE_ID: 38ffc2d9-cf1b-80c8-9427-c8506745362a -->

<!-- CONCEPT_NAME: REST Architecture & Its Purpose -->

<!-- REF_ANSWER: REST is an architecture because it defines how to structure and organize client-server interactions using existing protocols (HTTP), rather than defining the protocol itself. This distinction allows REST to be protocol-agnostic and leverage the existing HTTP infrastructure (firewalls, web servers, caching mechanisms) that are already universally deployed, making integration seamless across heterogeneous systems without requiring new protocol implementations. -->

**Q:** Why is REST classified as an architecture rather than a protocol, and what practical advantage does this distinction provide when integrating a weather app with a meteorological database?
**Answer:** REST does not define a fundamental set of rules for the digital transactions in data communication. It instead defines a set of constraints that a system implementing an API communication protocol must follow to maintain uniformity and scalability. A benefit is that this uses existing, widely accessible protocols (HTTP) that most servers provide access to.
<!-- GRADED_ON: 2026-07-01 -->
<!-- ASSIGNED_SCORE: 4 -->
**System Feedback:** *The student correctly identifies REST as constraint-based rather than protocol-defining and recognizes the practical advantage of leveraging HTTP, but misses the key distinction that REST is architecture-agnostic (protocol-independent) and fails to explain how this enables seamless integration across heterogeneous systems without new protocol implementations.*

---
<!-- PAGE_ID: 38ffc2d9-cf1b-80c8-9427-c8506745362a -->

<!-- CONCEPT_NAME: REST Architecture & Its Purpose -->

<!-- REF_ANSWER: Representation (R) means data is exchanged in standardized formats like JSON or XML rather than raw, proprietary formats; State (S) refers to the current condition of a resource at a given moment; Transfer (T) means this representation is moved between client and server via HTTP. Together, they decouple the internal data structure of a system from how it communicates, allowing a weather app to request data from any meteorological database regardless of its internal format. -->

**Q:** Explain the three components of 'Representational State Transfer' and how each addresses the problem of communicating with systems in different data formats.
**Answer:** Representation- raw data is not passed, instead some abstraction of it. State- current state. Transfer- data is moved via the HTTP protocol.
<!-- GRADED_ON: 2026-07-01 -->
<!-- ASSIGNED_SCORE: 3 -->
**System Feedback:** *The student correctly identifies the three components and grasps the basic mechanics of REST, but fails to explain the critical insight that standardized formats (JSON, XML) decouple internal system structures from communication protocols—missing the core problem REST solves regarding format interoperability.*

---
<!-- PAGE_ID: 38ffc2d9-cf1b-80c8-9427-c8506745362a -->

<!-- CONCEPT_NAME: REST Architecture & Its Purpose -->

<!-- REF_ANSWER: Maintaining shared state would violate REST's statelessness constraint, making systems tightly coupled, harder to scale horizontally, and vulnerable to consistency issues if a server crashes or is replaced. Statelessness ensures each request is independent and complete, allowing any server instance to handle any request without knowledge of prior interactions, which is essential for distributed, scalable systems. -->

**Q:** What would be the consequence if REST required clients and servers to maintain shared state or memory of previous interactions?
**Answer:** I do not know.
<!-- GRADED_ON: 2026-07-01 -->
<!-- ASSIGNED_SCORE: 1 -->
**System Feedback:** *The student provided no answer, demonstrating a complete lack of understanding of REST's statelessness constraint and its critical role in enabling scalability, loose coupling, and fault tolerance in distributed systems.*

---
## Concept: Resource-Oriented Design & HTTP Methods

<!-- PAGE_ID: 38ffc2d9-cf1b-80c8-9427-c8506745362a -->

<!-- CONCEPT_NAME: Resource-Oriented Design & HTTP Methods -->

<!-- REF_ANSWER: POST to /users creates a new user; PATCH to /users/{id} partially updates only the email field without overwriting other attributes; DELETE to /users/{id} removes the user. POST is used for creation because it creates a new resource; PATCH is used for partial updates to avoid accidentally overwriting unspecified fields (unlike PUT, which replaces the entire resource); DELETE is the standard removal operation. -->

**Q:** Design a RESTful endpoint structure for a user management system and specify which HTTP method you would use to add a new user, modify only a user's email address, and remove a user account. Justify your method choices.
**Answer:** I do not know.
<!-- GRADED_ON: 2026-07-01 -->
<!-- ASSIGNED_SCORE: 1 -->
**System Feedback:** *The student provided no answer, demonstrating a complete lack of understanding of RESTful API design principles, HTTP methods (POST, PATCH, DELETE), and their appropriate use cases for user management operations.*

---
<!-- PAGE_ID: 38ffc2d9-cf1b-80c8-9427-c8506745362a -->

<!-- CONCEPT_NAME: Resource-Oriented Design & HTTP Methods -->

<!-- REF_ANSWER: Assigning unique URLs to resources leverages the uniform interface constraint and allows REST to reuse HTTP's built-in infrastructure (caching, routing, security policies, load balancing). URLs become the canonical identifier for resources, making APIs more discoverable, cacheable, and compatible with existing web infrastructure. This also enforces a consistent, hierarchical structure that is intuitive and self-documenting. -->

**Q:** Why does REST assign each resource its own URL rather than using a single endpoint with different command parameters (e.g., /api?action=get&resource=cities&id=san-jose)?
**Answer:** I do not know.
<!-- GRADED_ON: 2026-07-01 -->
<!-- ASSIGNED_SCORE: 1 -->
**System Feedback:** *The student provided no answer, demonstrating a complete lack of understanding of REST's design principle that unique resource URLs enable HTTP infrastructure reuse (caching, routing, security) and create self-documenting, discoverable APIs—a fundamental concept in modern API design.*

---
<!-- PAGE_ID: 38ffc2d9-cf1b-80c8-9427-c8506745362a -->

<!-- CONCEPT_NAME: Resource-Oriented Design & HTTP Methods -->

<!-- REF_ANSWER: GET is idempotent and should not modify server state; using it to create records violates REST semantics and breaks caching (caches assume GET requests are safe and cacheable). This would cause unpredictable behavior with proxies and CDNs, make the API non-idempotent, and confuse other developers. POST is the correct method because it signals intent to create a new resource and is not cached by default, ensuring the creation actually occurs. -->

**Q:** A developer mistakenly uses GET to create a new database record instead of POST. What architectural and practical problems could this cause?
**Answer:** Well, the new resource record will simply not be created. An error will be returned because that resource doesn't exist.
<!-- GRADED_ON: 2026-07-01 -->
<!-- ASSIGNED_SCORE: 1 -->
**System Feedback:** *The student's answer is fundamentally incorrect—GET requests to create records would likely succeed (violating REST semantics and caching assumptions), not fail; the critical issues are architectural violations of idempotency, broken caching behavior with proxies/CDNs, and API confusion, not a simple "resource doesn't exist" error.*

---
## Concept: RESTful Constraints & HTTP Status Codes

<!-- PAGE_ID: 38ffc2d9-cf1b-80c8-9427-c8506745362a -->

<!-- CONCEPT_NAME: RESTful Constraints & HTTP Status Codes -->

<!-- REF_ANSWER: Violating the layered system constraint breaks load balancing and horizontal scaling. If clients are hardcoded to specific servers, adding new servers, removing failed ones, or redistributing load becomes impossible without updating all clients. This creates a single point of failure, prevents transparent upgrades, and makes the system brittle. The layered constraint allows intermediaries (load balancers, proxies, caches) to operate transparently between client and server. -->

**Q:** A REST API violates the layered system constraint by requiring clients to know the exact physical server they are communicating with. What scalability and maintenance problems would this create?
**Answer:** I do not know.
<!-- GRADED_ON: 2026-07-01 -->
<!-- ASSIGNED_SCORE: 1 -->
**System Feedback:** *The student provided no answer; a complete understanding of how the layered system constraint enables load balancing, horizontal scaling, and transparent intermediaries was required to address the scalability and maintenance problems created by client-server coupling.*

---
<!-- PAGE_ID: 38ffc2d9-cf1b-80c8-9427-c8506745362a -->

<!-- CONCEPT_NAME: RESTful Constraints & HTTP Status Codes -->

<!-- REF_ANSWER: A 404 (Not Found) indicates the resource the client requested does not exist on the server—the request was well-formed and valid, but the target resource is absent. A 400 (Bad Request) indicates the client's request itself is malformed or invalid (e.g., missing required fields, invalid syntax, incorrect data types)—the server cannot process it regardless of whether the resource exists. 404 is a resource problem; 400 is a request problem. -->

**Q:** Distinguish between a 404 status code and a 400 status code in terms of what each tells the client about the nature of the request failure.
**Answer:** 404 is an error on the server side. 400 is a general error.
<!-- GRADED_ON: 2026-07-01 -->
<!-- ASSIGNED_SCORE: 1 -->
**System Feedback:** *The answer fundamentally mischaracterizes both status codes: 404 is not a server-side error but rather indicates a missing resource despite a well-formed request, while 400 specifically indicates a malformed client request (not a "general error"), making this response technically incorrect on both counts.*

---
<!-- PAGE_ID: 38ffc2d9-cf1b-80c8-9427-c8506745362a -->

<!-- CONCEPT_NAME: RESTful Constraints & HTTP Status Codes -->

<!-- REF_ANSWER: Cacheability allows responses to be stored by clients, proxies, and CDNs, reducing redundant requests to the server and improving latency. Developers must explicitly mark responses because not all data should be cached (e.g., user-specific or time-sensitive data); caching stale data could cause incorrect behavior. By declaring cacheability, developers enable infrastructure to optimize performance while preventing cache-related bugs and security issues. -->

**Q:** Explain how the cacheability constraint in REST improves system performance and why a developer must explicitly mark responses as cacheable or non-cacheable.
**Answer:** If a response is cachable, the client knows how often it should send requests, ensuring that the server is not fielding more requests than necessary .
<!-- GRADED_ON: 2026-07-01 -->
<!-- ASSIGNED_SCORE: 2 -->
**System Feedback:** *The student correctly identifies that cacheability reduces redundant requests, but fundamentally misunderstands the mechanism—cacheability doesn't tell clients "how often to send requests"; rather, it permits responses to be stored and reused by clients, proxies, and CDNs, and critically omits why developers must *explicitly* mark responses (to prevent caching of sensitive/time-sensitive data that could cause security and correctness issues).*
