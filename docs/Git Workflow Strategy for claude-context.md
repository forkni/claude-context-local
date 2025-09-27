 Git Workflow Strategy for claude-context-local Repository (Revised)

 Current Situation Analysis

- Current branch: development with 50+ uncommitted files
- Branch differences: 768 files differ between main and development (mostly _archive/)
- _archive/ directory: Contains 738+ files that should be LOCAL ONLY
- Development files: CLAUDE.md, MEMORY.md should be in development but not main
- Test reorganization: Tests moved from root to unit/integration subdirectories
- run_benchmarks.bat: Part of start_mcp_server.bat menu structure, should be PUBLIC

 Revised Git Workflow Strategy

 1. Create Git Workflow Documentation (GIT_WORKFLOW.md)

 This file will contain:

- Three-tier structure: local → development → main
- Commit procedures and file management
- Public release checklist

 2. Update .gitignore for BOTH Branches

 Add to .gitignore (affects both development and main):

# Local-only content (never commit)

 _archive/
 benchmark_results/

# Development-specific (only in development branch)

 CLAUDE.md
 MEMORY.md

 3. Remove _archive/ from Git History

 Since _archive/ is already tracked, we need to remove it:

# Remove from git but keep local files

 git rm -r --cached _archive/
 echo "_archive/" >> .gitignore
 git add .gitignore
 git commit -m "chore: Remove _archive from version control (keep local only)"

 4. Commit to Development Branch

# Stage test reorganization

 git add tests/unit/
 git add tests/integration/
 git rm tests/test_*.py

# Stage modified files

 git add -u

# Stage new public files

 git add run_benchmarks.bat  # PUBLIC - part of menu system
 git add evaluation/token_efficiency_evaluator.py
 git add docs/TESTING_GUIDE.md
 git add scripts/batch/start_mcp_*.bat
 git add scripts/powershell/hf_auth.ps1

# Keep CLAUDE.md and MEMORY.md in development

 git add CLAUDE.md MEMORY.md

# Commit

 git commit -m "feat: Complete project rename and test suite overhaul

- Renamed project from Claude-context-MCP to claude-context-local
- Reorganized tests into unit/integration subdirectories
- Fixed all test failures (184 unit tests, all integration tests passing)
- Added robust HuggingFace authentication handling
- Improved test mocking and error handling
- Added benchmarking system with run_benchmarks.bat
- Removed _archive from version control (local-only)

 Co-Authored-By: Claude <noreply@anthropic.com>"

 git push origin development

 5. Main Branch Release Process

# 1. Switch to main

 git checkout main

# 2. Merge from development

 git merge development --no-commit --no-ff

# 3. Remove development-only files before commit

 git rm --cached CLAUDE.md MEMORY.md

# 4. Ensure _archive is not included (already in .gitignore)

 git status  # Verify _archive is not listed

# 5. Commit public version

 git commit -m "Release: v2.1.0 - Complete test suite with benchmarking

- Full test suite reorganization
- Benchmarking system included
- All tests passing
- Windows-optimized installation"

# 6. Push to main

 git push origin main

 6. Three-Tier File Management

 | File/Directory     | Local | Development | Main (Public) |
 |--------------------|-------|-------------|---------------|
 | _archive/          | ✅     | ❌           | ❌             |

 | CLAUDE.md          | ✅     | ✅           | ❌             |

 | MEMORY.md          | ✅     | ✅           | ❌             |

 | run_benchmarks.bat | ✅     | ✅           | ✅             |

 | benchmark_results/ | ✅     | ❌           | ❌             |

 | tests/             | ✅     | ✅           | ✅             |

 | Core code          | ✅     | ✅           | ✅             |

 7. Create GIT_WORKFLOW.md

# Git Workflow for claude-context-local

## Three-Tier Structure

### 1. Local Machine (Working Directory)

- Contains EVERYTHING including _archive/ (738+ files)
- _archive/ is NEVER committed to any branch
- benchmark_results/ stays local (generated files)

### 2. Development Branch (Internal)

- Contains all code + CLAUDE.md + MEMORY.md
- Does NOT contain _archive/ or benchmark_results/
- Used for internal development with full context

### 3. Main Branch (Public)

- Clean public release
- Excludes CLAUDE.md, MEMORY.md
- Includes run_benchmarks.bat (part of menu system)
- Professional presentation for users

## Commit Workflow

 1. **Local Development**

- Work with full _archive/ available locally
- _archive/ automatically ignored by git

 2. **Development Branch Commits**

  ```bash
  git add .                                                                                                                     
  git commit -m "feat: description"                                                                                             
  git push origin development                                                                                                   
                                 
 3. Main Branch Release                                                                                                           
 git checkout main                                                                                                                
 git merge development --no-commit                                                                                                
 git rm --cached CLAUDE.md MEMORY.md                                                                                              
 git commit -m "Release: version"                                                                                                 
 git push origin main                                                                                                             
                                 
 File Management Rules                                                                                                            
                                 
 - _archive/: LOCAL ONLY - Never commit                                                                                           
 - CLAUDE.md/MEMORY.md: Development only                                                                                          
 - run_benchmarks.bat: PUBLIC - Part of menu                                                                                      
 - tests/: PUBLIC - Full transparency                                                                                             
                                 
 #### 8. **Update CLAUDE.md**                                                                                                     
 Add section:                                                                                                                     
 ```markdown                                                                                                                      
 ## Git Workflow & Branch Management                                                                                              
                                 
 ### Three-Tier File Structure                                                                                                    
 1. **Local Only**: _archive/ (738+ files) - NEVER committed                                                                      
 2. **Development Branch**: Includes CLAUDE.md, MEMORY.md                                                                         
 3. **Main Branch**: Public release without development files                                                                     
                                 
 ### Critical Rules                                                                                                               
 - **_archive/ is LOCAL ONLY** - Contains 738+ historical files                                                                   
 - **run_benchmarks.bat is PUBLIC** - Part of start_mcp_server.bat menu                                                           
 - **Tests are PUBLIC** - Full transparency for users                                                                             
                                 
 ### Commit Process                                                                                                               
 Always: Local → Development → Main (with cleanup)                                                                                
                                 
 Immediate Actions                                                                                                                
                                 
 1. Update .gitignore to exclude _archive/ from ALL branches                                                                      
 2. Remove _archive/ from git while keeping local files                                                                           
 3. Create GIT_WORKFLOW.md with three-tier documentation                                                                          
 4. Commit to development with CLAUDE.md, MEMORY.md, run_benchmarks.bat                                                           
 5. Update CLAUDE.md with git workflow section                                                                                    
 6. Prepare main branch without development files                                                                                 
                                 
 Benefits of Revised Strategy                                                                                                     
                                 
 ✅ Massive space savings: _archive/ (738+ files) stays local only                                                                

 ✅ Development context: CLAUDE.md/MEMORY.md in development branch                                                                

 ✅ Clean public repo: Professional main branch                                                                                   

 ✅ Menu integrity: run_benchmarks.bat available in public                                                                        

 ✅ Full test transparency: All tests public                                                                                      

 ✅ Sustainable workflow: Clear three-tier structure                                                                              

                                 
 This ensures _archive/ never leaves your local machine while maintaining proper separation between development and public        
 branches.  
