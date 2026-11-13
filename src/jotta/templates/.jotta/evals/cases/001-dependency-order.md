# Case 001: dependency order

Create a disposable PRD with F01, F02 depending on F01 and F03 depending on F02. Run the product scope.

Passes if F02 does not start before F01 is proven complete and F03 does not start before F02.
