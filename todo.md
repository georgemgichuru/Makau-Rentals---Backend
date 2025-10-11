# TODO: Fix comprehensive_test_v2.ps1 errors

- [x] Define tenant headers after tenant login (section 7)
- [x] Change unit type creation to send 'unit_count' instead of 'number_of_units'
- [x] Update units response handling to use array indexing instead of .results
- [x] Change reminder preferences update to PATCH method with tenant token
- [x] Fix reports response indexing to use array instead of .results
- [x] Test the script after fixes (runs successfully until deposit payment, which fails as expected without M-Pesa setup)
