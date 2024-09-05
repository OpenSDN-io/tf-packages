%define         _contrailetc /etc/contrail
%define         _distropkgdir %{_sbtop}tools/packages/rpm/%{name}

%if 0%{?_buildTag:1}
%define         _relstr      %{_buildTag}
%else
%define         _relstr      %(date -u +%y%m%d%H%M)
%endif

%if 0%{?_srcVer:1}
%define         _verstr      %{_srcVer}
%else
%define         _verstr      1
%endif

%if 0%{?_opt:1}
%define         _sconsOpt      %{_opt}
%else
%define         _sconsOpt      debug
%endif

Name:             contrail-nodemgr
Version:          %{_verstr}
Release:          %{_relstr}%{?dist}
Summary:          Contrail Nodemgr %{?_gitVer}

Group:            Applications/System
License:          Commercial
URL:              http://www.juniper.net/
Vendor:           Juniper Networks Inc

Requires:         contrail-lib >= %{_verstr}-%{_relstr}
Requires:         python3-contrail >= %{_verstr}-%{_relstr}
%if 0%{?rhel} < 8
Requires:         ntp
%endif
Requires:         python3-setuptools

BuildRequires: bison
BuildRequires: boost169-devel = 1.69.0
BuildRequires: flex
BuildRequires: gcc
BuildRequires: gcc-c++
BuildRequires: make

%description
Contrail Nodemgr package

%prep

%build
pushd %{_sbtop}/controller

scons --opt=%{_sconsOpt} -U contrail-nodemgr
if [ $? -ne 0 ] ; then
  echo "build failed"
  exit -1
fi
popd

%install

# Setup directories

pushd %{_sbtop}

#install files
install -d -m 755 %{buildroot}%{_bindir}

# install pysandesh files
%define _build_dist %{_sbtop}/build/%{_sconsOpt}
install -d -m 755 %{buildroot}

popd

mkdir -p build/python_dist
cd build/python_dist

last=$(ls -1 --sort=v -r %{_build_dist}/nodemgr/dist/*.tar.gz | head -n 1| xargs -i basename {})
echo "DBG: %{_build_dist}/nodemgr/dist/ last tar.gz = $last"
tar zxf %{_build_dist}/nodemgr/dist/$last
pushd ${last//\.tar\.gz/}
%{__python3} setup.py install --root=%{buildroot} --no-compile
popd

%files
%defattr(-,root,root,-)
%{_bindir}/contrail-nodemgr
%{python3_sitelib}/nodemgr
%{python3_sitelib}/nodemgr-*

%post
set -e
%{__python3} -m pip install --no-compile \
  'bottle>= 0.12.21' 'psutil!=5.5.0,!=5.5.1,>=0.6.0' 'gevent<1.5.0' 'fysom' 'PyYAML>=5.1,<6' 'netaddr<1'

%changelog
