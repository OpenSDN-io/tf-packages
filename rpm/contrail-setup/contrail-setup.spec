%define       _contrailopt /opt/contrail
%define       _distropkgdir %{_sbtop}tools/packages/rpm/%{name}
%define       _provdir      %{_sbtop}tools/provisioning

%if 0%{?_buildTag:1}
%define       _relstr  %{_buildTag}
%else
%define       _relstr  %(date -u +%y%m%d%H%M)
%endif
%if 0%{?_fileList:1}
%define       _flist   %{_fileList}
%else
%define       _flist   None
%endif
%if 0%{?_srcVer:1}
%define       _verstr  %{_srcVer}
%else
%define       _verstr  1
%endif
%if 0%{?_skuTag:1}
%define       _sku     %{_skuTag}
%else
%define       _sku     None
%endif

Name:          contrail-setup
Version:      %{_verstr}
Release:      %{_relstr}%{?dist}
Summary:      Contrail Setup %{?_gitVer}
BuildArch:    noarch

Group:        Applications/System
License:      Commercial
URL:          http://www.juniper.net/
Vendor:       Juniper Networks Inc

Requires:      tar
Requires:      net-tools

%description
Contrail Setup package with scripts for provisioning

%prep
%if 0%{?_pre_cleanup:1}
rm -rf %{buildroot}
%endif

%build

pushd %{_sbtop}/controller/src/config
tar cvfz %{_builddir}/cfgm_utils.tgz utils
popd

pushd %{_sbtop}/controller/src/dns/scripts
tar cvfz %{_builddir}/dns_scripts.tgz *
popd

%install
# Setup directories
install -d -m 755 %{buildroot}%{_contrailopt}
install -d -m 755 %{buildroot}%{_contrailopt}
install -d -m 755 %{buildroot}%{_contrailopt}/bin
install -d -m 777 %{buildroot}%{_localstatedir}/log/contrail
install -d -m 755 %{buildroot}%{_contrailopt}/contrail_packages
install -d -m 755 %{buildroot}%{_contrailopt}/python_packages
# install files
pushd %{_sbtop}
echo BUILDID=`echo %{_relstr} | cut -d "~" -f1` > %{buildroot}%{_contrailopt}/contrail_packages/VERSION
install -p -m 755 %{_distropkgdir}/README %{buildroot}%{_contrailopt}/contrail_packages/README
install -p -m 755 %{_distropkgdir}/contrail_ifrename.sh %{buildroot}%{_contrailopt}/bin/getifname.sh
popd
# install etc files
install -p -m 644 %{_builddir}/cfgm_utils.tgz  %{buildroot}%{_contrailopt}/cfgm_utils.tgz
install -p -m 644 %{_builddir}/dns_scripts.tgz  %{buildroot}%{_contrailopt}/dns_scripts.tgz
install -d -m 755 %{buildroot}/etc/contrail

%post
cd %{_contrailopt}
tar xzvf cfgm_utils.tgz
tar xzvf dns_scripts.tgz -C utils
%{__python3} -m pip install --no-compile \
  -r utils/requirements.txt
ln -sbf %{_contrailopt}/bin/* %{_bindir}

%files
%defattr(-, root, root)
%{_contrailopt}/bin
%{_contrailopt}/contrail_packages/VERSION
%{_contrailopt}/contrail_packages/README
%{_contrailopt}/cfgm_utils.tgz
%{_contrailopt}/dns_scripts.tgz
%if 0%{?_fileList:1}
    /etc/contrail/rpm_list.txt
%endif
/etc/contrail
%dir %attr(0777, contrail, contrail) %{_localstatedir}/log/contrail

%changelog
* Fri Sep 13 2024 Anddrey Pavlov <apavlov@progmaticlab.compile
- use python3 for all
* Wed Aug 21 2019 Dheeraj Gautam <dgautam@juniper.net>
- Removed contrail-provisioning and call to create_pkg_list_file.py
* Mon Dec 14 2015 Nagendra Maynattamai <npchandran@juniper.net>
- Removed 1. Dependency for python-pip, 2. Dont package sources of fabric, paramiko, pycrypto and zope as tgz
