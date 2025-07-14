# Pull Request Template

## 📋 Description

**Brief description of changes**
Provide a clear and concise description of what this PR does.

**Related Issue(s)**
- Fixes #issue_number
- Addresses #issue_number
- Related to #issue_number

## 🔄 Type of Change

**Please select the type of change:**
- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] 🔧 Refactoring (no functional changes)
- [ ] ⚡ Performance improvement
- [ ] 🧪 Test improvement
- [ ] 🔒 Security fix

## 🧪 Testing

**How has this been tested?**
- [ ] Unit tests
- [ ] Integration tests
- [ ] End-to-end tests
- [ ] Manual testing

**Test Configuration:**
- OS: [e.g. Windows 11, macOS 13, Ubuntu 22.04]
- Python Version: [e.g. 3.9.7]
- Test Environment: [e.g. local, docker, CI]

**New tests added:**
- [ ] Unit tests for new functionality
- [ ] Integration tests for new features
- [ ] Updated existing tests
- [ ] No tests needed (explain why)

## 📸 Screenshots/Examples

**Before and After (if UI changes)**
| Before | After |
|--------|-------|
| screenshot/code | screenshot/code |

**Code Examples:**
```python
# Example of new functionality
result = new_feature(parameters)
```

## 📋 Checklist

**Code Quality:**
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] My changes generate no new warnings
- [ ] I have added type hints where appropriate

**Testing:**
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Integration tests pass with my changes

**Documentation:**
- [ ] I have made corresponding changes to the documentation
- [ ] I have updated the README if needed
- [ ] I have updated docstrings for new/modified functions
- [ ] I have added examples for new functionality

**Dependencies:**
- [ ] I have checked that new dependencies are necessary
- [ ] I have updated requirements files if needed
- [ ] I have verified compatibility with supported Python versions

## 🔄 Migration Guide

**Breaking Changes (if applicable):**
Describe any breaking changes and provide migration instructions.

**Configuration Changes:**
```yaml
# Old configuration
old_setting: value

# New configuration  
new_setting: value
```

## 📊 Performance Impact

**Performance Considerations:**
- [ ] No performance impact
- [ ] Performance improvement (describe)
- [ ] Potential performance regression (explain and justify)

**Benchmarks (if applicable):**
```
Before: X operations/second
After: Y operations/second
Improvement: Z%
```

## 🔒 Security Considerations

**Security Impact:**
- [ ] No security impact
- [ ] Fixes security vulnerability
- [ ] Introduces new security considerations (explain)
- [ ] Requires security review

## 📚 Documentation Updates

**Documentation changes included:**
- [ ] Code documentation (docstrings)
- [ ] User guide updates
- [ ] API documentation
- [ ] Configuration documentation
- [ ] Examples and tutorials
- [ ] CHANGELOG.md entry

## 🎯 Deployment Notes

**Special deployment considerations:**
- [ ] Database migrations required
- [ ] Configuration updates required
- [ ] Manual intervention needed
- [ ] Backward compatibility maintained

## 🔗 Related PRs

**Related or dependent PRs:**
- Depends on #pr_number
- Related to #pr_number
- Supersedes #pr_number

## 🧪 Testing Instructions

**How to test this PR:**

1. **Setup:**
   ```bash
   git checkout feature/branch-name
   pip install -e .
   ```

2. **Test Cases:**
   ```bash
   # Test case 1
   wmat command --options
   
   # Test case 2
   wmat other-command --different-options
   ```

3. **Expected Results:**
   - Describe expected behavior
   - Include any specific output to look for

## 📋 Review Guidelines

**Areas that need special attention:**
- [ ] Algorithm correctness
- [ ] Error handling
- [ ] Performance implications
- [ ] Security implications
- [ ] API design
- [ ] User experience

**Questions for reviewers:**
1. Is the approach sound?
2. Are there any edge cases I missed?
3. Is the code maintainable and readable?

## 📝 Additional Notes

**Implementation details:**
Explain any complex implementation decisions or trade-offs made.

**Future improvements:**
Mention any follow-up work or improvements that could be made.

**Known limitations:**
Document any known limitations or temporary workarounds.

---

**Reviewer Assignment:**
@TejasMate - Please review when ready

**Labels:**
Please add appropriate labels (enhancement, bug, documentation, etc.)

**Milestone:**
Associate with appropriate milestone if applicable
