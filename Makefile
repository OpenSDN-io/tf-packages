MKFILE_DIR 	:= $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
SB_TOP 			:= $(MKFILE_DIR:tools/packages/=)

SPEC_DIR 			:= $(MKFILE_DIR)rpm
SPEC_FILES 		:= $(wildcard $(SPEC_DIR)/*/*.spec)
PACKAGES 			:= $(patsubst %.spec,rpm-%,$(notdir $(SPEC_FILES)))
DEPENDENCIES 	:= $(patsubst %.spec,dep-%,$(notdir $(SPEC_FILES)))

DEBUGINFO    ?= TRUE
TOPDIR       ?= $(SB_TOP)
SCONSOPT     ?= production
SRCVER       ?= $(shell cat $(SB_TOP)controller/src/base/version.info)
KVERS        ?= $(shell $(MKFILE_DIR)utils/get_kvers.sh)
BUILDTAG     ?= $(shell date +%m%d%Y%H%M)
SKUTAG       ?= ocata
ENABLEMLX    ?= TRUE
ENABLEN3K    ?= TRUE
MANIFESTFILE ?= $(SB_TOP).repo/manifest.xml

OS_DISTR      ?= $(shell cat /etc/os-release | grep '^ID=' | cut -d = -f 2 | sed  's/\"//g')
OS_DISTR_VER  ?= $(shell cat /etc/os-release | grep '^VERSION_ID' | cut -d = -f 2 | tr -d '"')

ifeq ($(CONTRAIL_BUILD_FROM_SOURCE),true)
	RPMBUILD_MODE := -bi
else
	RPMBUILD_MODE := -bb
endif

RPMBUILD_FLAGS ?=
DEPBUILD_FLAGS ?=
ifeq ($(OS_DISTR), rhel)
	ifeq ($(OS_DISTR_VER), 8.4)
		RPMBUILD_FLAGS += --define "__python %__python2"
		RPMBUILD_FLAGS += --define "__brp_mangle_shebangs %{nil}"
		RPMBUILD_FLAGS += --define "__requires_exclude /usr/bin/python"
# disable debugsources - it generates empty debugsources.list because of src
# is outside of build dir but starting from rhel8 debugsources where moved to
# separate debugsources rpms that fails build because of empty  debugsources.list file
# https://pagure.io/releng/issue/6863#comment-467612
# https://bugzilla.redhat.com/show_bug.cgi?id=1479198
		RPMBUILD_FLAGS += --define "_debugsource_template %{nil}"
		RPMBUILD_FLAGS += --define "_debuginfo_subpackages %{nil}"
		DEPBUILD_FLAGS += --define "__python %__python2"
	endif
endif

RPMBUILD_FLAGS += --define "_sbtop $(SB_TOP)"
RPMBUILD_FLAGS += --define "_topdir $(TOPDIR)"
RPMBUILD_FLAGS += --define "_opt $(SCONSOPT)"
RPMBUILD_FLAGS += --define "_kVers $(KVERS)"
RPMBUILD_FLAGS += --define "_skuTag $(SKUTAG)"
RPMBUILD_FLAGS += --define "_srcVer $(SRCVER)"
RPMBUILD_FLAGS += --define "_buildTag $(BUILDTAG)"

ifdef DPDK_BUILD_DIR
	RPMBUILD_FLAGS += --define "_dpdk_build_dir $(DPDK_BUILD_DIR)"
endif

ifeq ($(ENABLEMLX),TRUE)
	RPMBUILD_FLAGS += --define "_enableMellanox $(ENABLEMLX)"
	DEPBUILD_FLAGS += --define "_enableMellanox $(ENABLEMLX)"
endif

ifeq ($(ENABLEN3K),TRUE)
	RPMBUILD_FLAGS += --define "_enableIntelN3K $(ENABLEN3K)"
	DEPBUILD_FLAGS += --define "_enableIntelN3K $(ENABLEN3K)"
endif

ifeq ($(DEBUGINFO),TRUE)
	RPMBUILD_FLAGS += --with debuginfo
else
	RPMBUILD_FLAGS += --without debuginfo
endif

ifdef MANIFESTFILE
	RPMBUILD_FLAGS += --define "_manifestFile $(MANIFESTFILE)"
endif

SCONSFLAGS := -j $(shell nproc)

export BUILD_ONLY := TRUE
export SCONSFLAGS := $(SCONSFLAGS)

all: install-dnf dep rpm
	@echo $(PACKAGES)
	@echo $(DEPENDENCIES)

dep: install-dnf $(DEPENDENCIES) kernel-deps

install-dnf:
	@echo "Installing DNF package manager..."
	@sudo yum install -y dnf dnf-plugins-core

.PHONY: all rpm dep kernel-deps testdeps-rpms install-dnf

rpm: $(PACKAGES) testdeps-rpms

dep-%:
	$(eval SPECFILE = $(filter %/$(patsubst dep-%,%.spec,$@), $(SPEC_FILES)))
	@echo Installing dependencies for $(SPECFILE) DEPBUILD_FLAGS=$(DEPBUILD_FLAGS) ...
	@if command -v dnf > /dev/null; then \
		echo "Using dnf to install dependencies"; \
		sudo dnf builddep $(DEPBUILD_FLAGS) -y $(SPECFILE); \
	else \
		echo "dnf is not available, falling back to yum-builddep"; \
		sudo yum-builddep $(DEPBUILD_FLAGS) -y $(SPECFILE); \
	fi

kernel-deps:
	$(MKFILE_DIR)utils/install_kernels.sh

testdeps-rpms:
ifeq ($(CONTRAIL_BUILD_FROM_SOURCE),true)
	rpmbuild --noclean -bb --with testdepsonly $(RPMBUILD_FLAGS) $(SPEC_DIR)/contrail/contrail.spec
endif

rpm-%:
	$(eval SPECFILE = $(filter %/$(patsubst rpm-%,%.spec,$@), $(SPEC_FILES)))
	echo RPM build for $(SPECFILE) RPMBUILD_MODE=$(RPMBUILD_MODE) RPMBUILD_FLAGS=$(RPMBUILD_FLAGS) ...
	rpmbuild $(RPMBUILD_MODE) $(RPMBUILD_FLAGS) $(SPECFILE)

# depends to enable -j x option for make
rpm-contrail-web-core: rpm-contrail-web-controller

list:
	@echo $(sort $(patsubst rpm-%,%,$(PACKAGES)))

info:
	@echo SPEC_FILES=$(SPEC_FILES)
	@echo DEBUGINFO=$(DEBUGINFO)
	@echo MANIFESTFILE=$(MANIFESTFILE)
	@echo TOPDIR=$(TOPDIR)
	@echo SCONSOPT=$(SCONSOPT)
	@echo SRCVER=$(SRCVER)
	@echo KVERS=$(KVERS)
	@echo BUILDTAG=$(BUILDTAG)
	@echo SKUTAG=$(SKUTAG)
	@echo RPMBUILD_FLAGS=$(RPMBUILD_MODE) $(RPMBUILD_FLAGS)
