%define         _unpackaged_files_terminate_build 0
%define         _contrailetc /etc/contrail
%define         _contrailutils /opt/contrail/utils
%define         _fabricansible /opt/contrail/fabric_ansible_playbooks
%define         _distropkgdir %{_sbtop}tools/packages/rpm/%{name}
%define         _contraildns /etc/contrail/dns

%if 0%{?_kernel_dir:1}
%define         _osVer  %(cat %{_kernel_dir}/include/linux/utsrelease.h | cut -d'"' -f2)
%else
%define         _osVer       %(uname -r)
%endif
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
%if 0%{?_kVers:1}
%define         _kvers      %{_kVers}
%else
%define         _kvers      3.10.0-1160.25.1.el7.x86_64
%endif
%if 0%{?_opt:1}
%define         _sconsOpt      %{_opt}
%else
%define         _sconsOpt      debug
%endif

%global _dwz_low_mem_die_limit 0

%bcond_with testdepsonly
%bcond_without debuginfo

Name:           contrail
Version:        %{_verstr}
Release:        %{_relstr}%{?dist}
Summary:        Contrail

Group:          Applications/System
License:        ASL 2.0
URL:            www.opencontrail.org
Vendor:         OpenContrail Project.

BuildRequires: autoconf
BuildRequires: automake
BuildRequires: bison
# tpc
BuildRequires: boost169-devel
BuildRequires: cassandra-cpp-driver
BuildRequires: cassandra-cpp-driver-devel
#
BuildRequires: cmake
BuildRequires: cyrus-sasl-devel
BuildRequires: flex
BuildRequires: gcc
BuildRequires: gcc-c++
BuildRequires: grok-devel
%if ! 0%{?rhel}
BuildRequires: python3-sphinx
BuildRequires: python3-requests
BuildRequires: python3-lxml
%endif
BuildRequires: libcurl-devel
# tpc
BuildRequires: librdkafka-devel >= 1.5.0
#
BuildRequires: libstdc++-devel
BuildRequires: libtool
BuildRequires: libxml2-devel
BuildRequires: libzookeeper-devel
BuildRequires: lz4-devel
BuildRequires: make
%if 0%{?rhel} < 8
BuildRequires: openssl <= 1:1.0.2o
BuildRequires: openssl-devel <= 1:1.0.2o
%else
BuildRequires: compat-openssl10 <= 1:1.0.2o
BuildRequires: compat-openssl10-debugsource <= 1:1.0.2o
%endif
BuildRequires: protobuf
BuildRequires: protobuf-compiler
BuildRequires: protobuf-devel
BuildRequires: python3-devel
BuildRequires: python3-setuptools
BuildRequires: systemd-units
BuildRequires: tbb-devel
BuildRequires: tokyocabinet-devel
BuildRequires: unzip
BuildRequires: vim-common
BuildRequires: zlib-devel
BuildRequires: libcmocka-devel
BuildRequires: libxslt-devel
BuildRequires: PyYAML

%description
Contrail package describes all sub packages that are required to
run open contrail.

%if %{without testdepsonly}
%if %{with debuginfo}
%debug_package
%endif

%prep

%build

%install

pushd %{_sbtop}
scons --opt=%{_sconsOpt} --root=%{buildroot} --without-dpdk install
for kver in %{_kvers}; do
    echo "Kver = ${kver}"
    if ls /lib/modules/${kver}/build ; then
        sed 's/{kver}/%{_kver}/g' %{_distropkgdir}/dkms.conf.in.tmpl > %{_distropkgdir}/dkms.conf.in
        scons -c --opt=%{_sconsOpt} --kernel-dir=/lib/modules/${kver}/build build-kmodule
        scons --opt=%{_sconsOpt} --kernel-dir=/lib/modules/${kver}/build build-kmodule --root=%{buildroot}
    else
        echo "WARNING: kernel-devel-$kver is not installed, Skipping building vrouter for $kver"
    fi
done
mkdir -p %{buildroot}/_centos/tmp
popd

pushd %{buildroot}
mkdir -p %{buildroot}/centos
cp %{_distropkgdir}/dkms.conf.in %{buildroot}/centos/
(cd usr/src/vrouter && tar zcf %{buildroot}/_centos/tmp/contrail-vrouter-%{_verstr}.tar.gz .)
sed "s/__VERSION__/"%{_verstr}"/g" centos/dkms.conf.in > usr/src/vrouter/dkms.conf
rm  centos/dkms.conf.in
install -d -m 755 %{buildroot}/usr/src/modules/contrail-vrouter
install -p -m 755 %{buildroot}/_centos/tmp/contrail-vrouter*.tar.gz %{buildroot}/usr/src/modules/contrail-vrouter
rm %{buildroot}/_centos/tmp/contrail-vrouter*.tar.gz
rm -rf %{buildroot}/_centos
popd

#Build nova-contrail-vif
pushd %{_sbtop}
scons --opt=%{_sconsOpt} -U nova-contrail-vif
popd
pushd %{_sbtop}/build/noarch/nova_contrail_vif
%{__python3} setup.py install --root=%{buildroot} --no-compile
popd

# contrail-docs
# Move schema specific files to opserver
for mod_dir in %{buildroot}/usr/share/doc/contrail-docs/html/messages/*; do \
    if [ -d $mod_dir ]; then \
        for python_dir in %{buildroot}%{python_sitelib}; do \
            install -d -m 0755 -p $python_dir/opserver/stats_schema/`basename $mod_dir`; \
            for statsfile in %{buildroot}/usr/share/doc/contrail-docs/html/messages/`basename $mod_dir`/*_stats_tables.json; do \
                install -p -m 644 -t $python_dir/opserver/stats_schema/`basename $mod_dir`/ $statsfile; \
                rm -f $statsfile; \
            done \
        done \
    fi \
done

# Index files
%{__python3} %{_sbtop}/tools/packages/utils/generate_doc_index.py %{buildroot}/usr/share/doc/contrail-docs/html/messages

#Needed for agent container env
# install vrouter.ko at /opt/contrail/vrouter-kernel-modules to use with containers
for vrouter_ko in $(ls -1 %{buildroot}/lib/modules/*/extra/net/vrouter/vrouter.ko); do
  build_root=$(echo %{buildroot})
  kernel_ver=$(echo ${vrouter_ko#${build_root}/lib/modules/} | awk -F / '{print $1}')
  install -d -m 755 %{buildroot}/%{_contrailutils}/../vrouter-kernel-modules/$kernel_ver/
  install -p -m 755 $vrouter_ko %{buildroot}/%{_contrailutils}/../vrouter-kernel-modules/$kernel_ver/vrouter.ko
done

# contrail-tools package
install -p -m 755 %{_sbtop}/build/%{_sconsOpt}/vrouter/utils/dpdkinfo %{buildroot}/usr/bin/dpdkinfo

#Needed for vrouter-dkms
install -d -m 755 %{buildroot}/usr/src/vrouter-%{_verstr}
pushd %{buildroot}/usr/src/vrouter
find . -print | sed 's;^;'"%{buildroot}/usr/src/vrouter-%{_verstr}/"';'| xargs install -d -m 755

#Install the remaining files in /usr/share to /opt/contrail/utils
pushd %{buildroot}/usr/share/contrail
find . -print | sed 's;^;'"%{buildroot}%{_contrailutils}"';'| xargs install -d -m 755

#Needed for Lbaas
install -d -m 755 %{buildroot}/etc/sudoers.d/
echo 'Defaults:root !requiretty' >> %{buildroot}/contrail-lbaas
install -m 755 %{buildroot}/contrail-lbaas  %{buildroot}/etc/sudoers.d/contrail-lbaas

# Install section of contrail-utils package - START
install -d -m 755 %{buildroot}/usr/share/contrail-utils
# copy files present in /usr/share/contrail to /usr/share/contrail-utils
# LP 1668338
pushd %{buildroot}/usr/share/contrail/
find . -maxdepth 1 -type f -exec cp {} %{buildroot}/usr/share/contrail-utils/ \;
popd
# Create symlink to utils script at /usr/bin
pushd %{buildroot}/usr/bin
for scriptpath in %{buildroot}/usr/share/contrail-utils/*; do
  scriptname=$(basename $scriptpath)
  scriptname_no_ext=${scriptname%.*}
  # avoid conflicting with coreutils package for file /usr/bin/chmod
  # LP #1668332
  if [[ $scriptname_no_ext == "chmod" ]]; then
    continue
  fi
  if [ ! -f $scriptname_no_ext ]; then
    ln -s ../share/contrail-utils/$scriptname $scriptname_no_ext
    echo /usr/bin/$scriptname_no_ext >> %{buildroot}/contrail-utils-bin-includes.txt
  else
    echo "WARNING: Skipping ( $scriptname_no_ext ) as a regular file of same name exists in /usr/bin/"
  fi
done
popd
# Install section of contrail-utils package - END

# Install section of contrail-config package - Start
install -d -m 755 %{buildroot}%{_fabricansible}
install -p -m 755 %{buildroot}/usr/bin/fabric_ansible_playbooks*.tar.gz %{buildroot}%{_fabricansible}/
# Install section of contrail-config package - End

# Install section of contrail-manifest package - Start
%if 0%{?_manifestFile:1}
mkdir -p %{buildroot}/opt/contrail/
cp %{_manifestFile} %{buildroot}/opt/contrail/manifest.xml
%endif
# Install section of contrail-manifest package - End

%files


%package vrouter
Summary:            Contrail vRouter
Group:              Applications/System

Requires:           contrail-vrouter-agent >= %{_verstr}-%{_relstr}
Requires:           contrail-lib >= %{_verstr}-%{_relstr}
# tpc
Requires:           xmltodict >= 0.7.0

%description vrouter
vrouter kernel module

The OpenContrail vRouter is a forwarding plane (of a distributed router) that
runs in the hypervisor of a virtualized server. It extends the network from the
physical routers and switches in a data center into a virtual overlay network
hosted in the virtualized servers.

The OpenContrail vRouter is conceptually similar to existing commercial and
open source vSwitches such as for example the Open vSwitch (OVS) but it also
provides routing and higher layer services (hence vRouter instead of vSwitch).

The package opencontrail-vrouter-dkms provides the OpenContrail Linux kernel
module.

%files vrouter
%defattr(-, root, root)
/lib/modules/*/extra/net/vrouter/vrouter.ko
/opt/contrail/vrouter-kernel-modules/*/vrouter.ko


%package vrouter-source
Summary:            Contrail vRouter

Group:              Applications/System

%description vrouter-source
Contrail vrouter source package

The OpenContrail vRouter is a forwarding plane (of a distributed router) that
runs in the hypervisor of a virtualized server. It extends the network from the
physical routers and switches in a data center into a virtual overlay network
hosted in the virtualized servers. The OpenContrail vRouter is conceptually
similar to existing commercial and open source vSwitches such as for example
the Open vSwitch (OVS) but it also provides routing and higher layer services
(hence vRouter instead of vSwitch).

The package opencontrail-vrouter-source provides the OpenContrail Linux kernel
module in source code format.

%files vrouter-source
/usr/src/modules/contrail-vrouter


%package config-openstack
Summary:            Config openstack

Group:              Applications/System

Requires:           contrail-config >= %{_verstr}-%{_relstr}
Requires:           ipmitool

%description config-openstack
Contrail config openstack package
This package contains the configuration management modules that interface with OpenStack.
%files config-openstack
%{python3_sitelib}/svc_monitor*
%{python3_sitelib}/vnc_openstack*
%attr(755, root, root) %{_bindir}/contrail-svc-monitor
/usr/share/contrail

%post config-openstack
set -ex

%{__python3} -m pip -v install --no-compile \
  future \
  python-ironicclient \
  python-ironic-inspector-client \
  python-keystoneclient \
  python-novaclient


%package -n python-contrail-vrouter-api
Summary:            Contrail vrouter api

Group:              Applications/System

%description -n python-contrail-vrouter-api
Contrail Virtual Router apis package

%files -n python-contrail-vrouter-api
%{python3_sitelib}/contrail_vrouter_api*


%package tools
Summary: Contrail tools
Group: Applications/System

Requires: tcpdump
Requires: wireshark
Requires: socat

%description tools
Contrail tools package

The package contrail-tools provides command line utilities to
configure and diagnose the OpenContrail Linux kernel module and other stuff.
It will be available in contrail-tools container

%files tools
%{_bindir}/dropstats
%{_bindir}/flow
%{_bindir}/mirror
%{_bindir}/mpls
%{_bindir}/nh
%{_bindir}/rt
%{_bindir}/vrfstats
%{_bindir}/vif
%{_bindir}/vxlan
%{_bindir}/vrouter
%{_bindir}/vrmemstats
%{_bindir}/qosmap
%{_bindir}/vifdump
%{_bindir}/vrftable
%{_bindir}/vrinfo
%{_bindir}/dpdkinfo
%{_bindir}/dpdkconf
%{_bindir}/dpdkvifstats.py
%{_bindir}/sandump
%{_bindir}/pkt_droplog.py
/usr/local/share/wireshark/init.lua
/usr/local/lib64/wireshark/plugins/main.lua
/usr/share/lua/5.1
/usr/local/lib64/wireshark/plugins/agent_hdr.lua

%package vrouter-utils
Summary: Contrail vRouter host tools
Group: Applications/System

%description vrouter-utils
Contrail vrouter utils contains only vif utility that should be copied to host.

%files vrouter-utils
%{_bindir}/vif
%{_bindir}/qosmap


%package vrouter-agent

Summary:            Contrail vRouter

Group:              Applications/System

Requires:           contrail-lib >= %{_verstr}-%{_relstr}
Requires:           xmltodict >= 0.7.0
Requires:           boost169
Requires:           boost169-devel

%description vrouter-agent
Contrail Virtual Router Agent package

OpenContrail is a network virtualization solution that provides an overlay
virtual-network to virtual-machines, containers or network namespaces. This
package provides the contrail-vrouter user space agent.

%files vrouter-agent
%defattr(-, root, root)
%attr(755, root, root) %{_bindir}/contrail-vrouter-agent*
%{_bindir}/contrail-tor-agent*
%{_bindir}/vrouter-port-control
%{_bindir}/contrail-compute-setup
%{_bindir}/contrail-toragent-setup
%{_bindir}/contrail-toragent-cleanup
%{_bindir}/contrail-vrouter-agent-health-check.py
%{_bindir}/contrail_crypt_tunnel_client.py
%{python3_sitelib}/contrail_vrouter_provisioning*

%post vrouter-agent
set -ex

%{__python3} -m pip -v install --no-compile \
  passlib \
  -r /opt/opensdn/pip/vrouter-provisioning/requirements.txt \


%package control
Summary:          Contrail Control
Group:            Applications/System

Requires:         contrail-lib >= %{_verstr}-%{_relstr}
Requires:         authbind
Requires:         xmltodict >= 0.7.0
Requires:         boost169
Requires:         boost169-devel

%description control
Contrail Control package

Control nodes implement the logically centralized portion of the control plane.
Not all control plane functions are logically centralized \u2013 some control
plane functions are still implemented in a distributed fashion on the physical
and virtual routers and switches in the network.

The control nodes use the IF-MAP protocol to monitor the contents of the
low-level technology data model as computed by the configuration nodes
thatdescribes the desired state of the network. The control nodes use a
combination of south-bound protocols to \u201cmake it so\u201d, i.e. to make
the actual state of the network equal to the desired state of the network.

In the initial version of the OpenContrail System these south-bound protocols
include Extensible Messaging and Presence Protocol (XMPP)to control the
OpenContrail vRouters as well as a combination of the Border Gateway Protocol
(BGP) and the Network Configuration (Netconf) protocols to control physical
routers. The control nodes also use BGP for state synchronization amongst each
other when there are multiple instances of the control node for scale-out and
high-availability reasons.

Control nodes implement a logically centralized control plane that is
responsible for maintaining ephemeral network state. Control nodes interact
with each other and with network elements to ensure that network state is
eventually consistent.

%files control
%defattr(-,root,root,-)
%attr(755, root, root) %{_bindir}/contrail-control*

%post control
set -ex
# Use authbind to bind contrail-control on a reserved port,
# with contrail user privileges
if [ ! -f /etc/authbind/byport/179 ]; then
  touch /etc/authbind/byport/179
  chown contrail. /etc/authbind/byport/179
  chmod 0755 /etc/authbind/byport/179
fi


%package -n python-opencontrail-vrouter-netns

Summary:            OpenContrail vRouter netns

Group:              Applications/System


Requires:           iptables
Requires:           iproute >= 3.1.0
Requires:           python3-devel


%description -n python-opencontrail-vrouter-netns
Contrail Virtual Router NetNS package

%files -n python-opencontrail-vrouter-netns
%defattr(-,root,root)
%{python3_sitelib}/opencontrail_vrouter_*
%{_bindir}/opencontrail-vrouter-*
/etc/sudoers.d/contrail-lbaas

%post -n python-opencontrail-vrouter-netns
set -ex

%{__python3} -m pip -v install --no-compile \
  -r /opt/opensdn/pip/vrouter-netns/requirements.txt \


%package lib
Summary:  Libraries used by the Contrail Virtual Router %{?_gitVer}
Group:              Applications/System
Obsoletes:          contrail-libs <= 0.0.1

%description lib
Libraries used by the Contrail Virtual Router.

%files lib
%defattr(-,root,root)
%{_libdir}/../lib/lib*.so*

%package config
Summary: Contrail Config
Group:              Applications/System

Requires:           python3-contrail >= %{_verstr}-%{_relstr}
Requires:           openssh-clients
# tpc bin
Requires:           uwsgi
Requires:           uwsgi-plugin-python36
Requires:           uwsgi-plugin-python36-gevent
# No such module for py3, (not in epel-release either)
# Requires:           compat-openssl10 <= 1:1.0.2o
Requires:           xmltodict >= 0.7.0
Requires:           openssl <= 1:1.0.2o

%description config
Contrail Config package

Configuration nodes are responsible for the management layer. The configuration
nodes provide a north-bound Representational State Transfer (REST) Application
Programming Interface (API) that can be used to configure the system or extract
operational status of the system. The instantiated services are represented by
objects in a horizontally scalable database that is described by a formal
service data model (more about data models later on).

The configuration nodes also contain a transformation engine (sometimes
referred to as a compiler) that transforms the objects in the high-level
service data model into corresponding more lower-level objects in the
technology data model. Whereas the high-level service data model describes what
services need to be implemented, the low-level technology data model describes
how those services need to be implemented.

The configuration nodes publish the contents of the low-level technology data
model to the control nodes using the Interface for Metadata Access Points
(IF-MAP) protocol. Configuration nodes keep a persistent copy of the intended
configuration state and translate the high-level data model into the lower
level model suitable for interacting with network elements. Both these are kept
in a NoSQL database.

# TODO: Update pinning of Python requirements (!!!IMPORTANT!!!)
%files config
%defattr(-,contrail,contrail,-)
%defattr(-,root,root,-)
%attr(755, root, root) %{_bindir}/contrail-api*
%attr(755, root, root) %{_bindir}/contrail-schema*
%attr(755, root, root) %{_bindir}/contrail-device-manager*
%{_bindir}/contrail-issu-pre-sync
%{_bindir}/contrail-issu-post-sync
%{_bindir}/contrail-issu-run-sync
%{_bindir}/contrail-issu-zk-sync
%{_fabricansible}/*.tar.gz
%{python3_sitelib}/schema_transformer*
%{python3_sitelib}/vnc_cfg_api_server*
%{python3_sitelib}/contrail_api_server*
%{python3_sitelib}/device_manager*
%{python3_sitelib}/job_manager*
%{python3_sitelib}/device_api*
%{python3_sitelib}/abstract_device_api*
%{python3_sitelib}/contrail_issu*
%docdir /usr/share/doc/contrail-config/
/usr/share/doc/contrail-config/

%post config
set -ex

%{__python3} -m pip -v install --no-compile \
  "cityhash" \
  "cassandra-driver>=3.16,<3.27" \
  "wheel" \
  "fysom" \
  "bottle<0.13" \
  "simplejson" \
  "kombu" \
  "configparser" \
  "inflection" \
  "attrdict" \
  "bitarray" \
  "requests" \
  "future" \
  "amqp" \
  "pycrypto" \
  "docker" \
  "gevent" \
  "jmespath" \
  "jsonschema" \
  "jsonpickle" \
  "lxml" \
  "python-keystoneclient" \
  "keystonemiddleware" \
  "keystoneauth1" \
  "kazoo" \
  "psutil" \
  "ncclient" \
  "pyroute2" \
  "pysnmp" \
  "PyYAML" \
  "subprocess32" \
  "python-swiftclient" \
  "xmltodict" \
  "zope-interface"
  
mkdir -p /etc/ansible
last=$(ls -1 --sort=v -r %{_fabricansible}/*.tar.gz | head -n 1| xargs -i basename {})
echo "DBG: %{_fabricansible} last tar.gz = $last"
tar -xvzf %{_fabricansible}/$last -C %{_fabricansible}
mv %{_fabricansible}/${last//\.tar\.gz/}/* %{_fabricansible}/
rmdir  %{_fabricansible}/${last//\.tar\.gz/}/
cat %{_fabricansible}/ansible.cfg > /etc/ansible/ansible.cfg


%package analytics
Summary:            Contrail Analytics
Group:              Applications/System

Requires:           contrail-lib >= %{_verstr}-%{_relstr}
Requires:           protobuf
Requires:           python3-contrail >= %{_verstr}-%{_relstr}
Requires:           redis >= 2.6.13-1
#tpc
Requires:           cassandra-cpp-driver
Requires:           grok
Requires:           libzookeeper
Requires:           librdkafka1 >= 1.5.0
Requires:           boost169
Requires:           boost169-devel
# for cassandra-driver
Requires:           Cython
Requires:           libev
Requires:           libev-devel
Requires:           net-snmp-devel

%description analytics
Contrail Analytics package
Analytics nodes are responsible for collecting, collating and presenting
analytics information for trouble shooting problems and for understanding
network usage. Each component of the OpenContrail System generates detailed
event records for every significant event in the system. These event records
are sent to one of multiple instances (for scale-out) of the analytics node
that collate and store the information in a horizontally scalable database
using a format that is optimized for time-series analysis and queries. the
analytics nodes have mechanism to automatically trigger the collection of more
detailed records when certain event occur; the goal is to be able to get to the
root cause of any issue without having to reproduce it. The analytics nodes
provide a north-bound analytics query REST API. Analytics nodes collect, store,
correlate, and analyze information from network elements, virtual or physical.
This information includes statistics,logs, events, and errors.

%files analytics
# Setup directories
%defattr(-,contrail,contrail,)
%defattr(-, root, root)
%attr(755, root, root) %{_bindir}/contrail-collector*
%attr(755, root, root) %{_bindir}/contrail-query-engine*
%attr(755, root, root) %{_bindir}/contrail-analytics-api*
%attr(755, root, root) %{_bindir}/contrail-alarm-gen*
%{python3_sitelib}/opserver*
%{python3_sitelib}/tf_snmp_collector*
%{python3_sitelib}/tf_topology*
%{_bindir}/contrail-logs
%{_bindir}/contrail-flows
%{_bindir}/contrail-sessions
%{_bindir}/contrail-db
%{_bindir}/contrail-stats
%{_bindir}/contrail-alarm-notify
%{_bindir}/contrail-logs-api-audit
%attr(755, root, root) %{_bindir}/tf-snmp-*
%attr(755, root, root) %{_bindir}/tf-topology
/usr/share/doc/contrail-analytics-api
/usr/share/mibs/netsnmp
/etc/contrail/snmp.conf
/opt/opensdn/pip*

%post analytics
set -ex

%{__python3} -m pip -v install --no-compile \
  -r /opt/opensdn/pip/opserver/requirements.txt \
  -r /opt/opensdn/pip/snmp-collector/requirements.txt \
  -r /opt/opensdn/pip/topology/requirements.txt |& tee /tmp/pip-analytics.log


%package dns
Summary:            Contrail Dns
Group:              Applications/System

Requires:           authbind
Requires:           boost169
Requires:           boost169-devel

%description dns
Contrail dns  package
DNS provides contrail-dns, contrail-named, contrail-rndc and
contrail-rndc-confgen daemons
Provides vrouter services

%post dns
set -ex
# Use authbind to bind amed on a reserved port,
# with contrail user privileges
if [ ! -f /etc/authbind/byport/53 ]; then
  touch /etc/authbind/byport/53
  chown contrail. /etc/authbind/byport/53
  chmod 0755 /etc/authbind/byport/53
fi

%files dns
%defattr(-,contrail,contrail,-)
%{_contraildns}
%config(noreplace) %{_contraildns}/applynamedconfig.py
%{_contraildns}/COPYRIGHT
%defattr(-, root, root)
%attr(755, root, root) %{_bindir}/contrail-named*
%{_bindir}/contrail-rndc
%{_bindir}/contrail-rndc-confgen
%attr(755, root, root) %{_bindir}/contrail-dns*
%docdir %{python3_sitelib}/doc/*


%package nova-vif
Summary:            Contrail nova vif driver
Group:              Applications/System

%description nova-vif
Contrail Nova Vif driver package

%files nova-vif
%defattr(-,root,root,-)
%{python3_sitelib}/nova_contrail_vif*
%{python3_sitelib}/vif_plug_vrouter
%{python3_sitelib}/vif_plug_contrail_vrouter


%package utils
Summary: Contrail utility sctipts.
Group: Applications/System

Requires:           lsof
Requires:           python3-contrail >= %{_verstr}-%{_relstr}

%description utils
Contrail utility sctipts package

%files -f %{buildroot}/contrail-utils-bin-includes.txt utils
%defattr(-, root, root)
/usr/share/contrail-utils/*


%package docs
Summary: Documentation for OpenContrail
Group: Applications/System

%description docs
OpenContrail is a network virtualization solution that provides an overlay
virtual-network to virtual-machines, containers or network namespaces.

This package contains the documentation for messages generated by OpenContrail
modules/daemons.

%files docs
%doc /usr/share/doc/contrail-docs/html/*


%package kube-manager
Summary:            Kubernetes network manager

Group:              Applications/System

Requires:    python3-contrail >= %{_verstr}-%{_relstr}

%description kube-manager
Contrail kubernetes network manager package
This package contains the kubernetes network management modules.
%files kube-manager
%{python3_sitelib}/kube_manager*
%{_bindir}/contrail-kube-manager

%post kube-manager
set -ex

%{__python3} -m pip -v install --no-compile \
  "requests" \
  "bitstring" \
  "bitarray" \
  "netaddr<1" \
  "greenlet" \
  "kombu" \
  "keystoneauth1" \
  "fysom" \
  "stevedore" \
  "simplejson" \
  "bottle<0.13" \
  "kazoo" \
  "enum34" \
  "gevent==22.10.1" \
  "cassandra-driver>=3.16,<3.27"


%package k8s-cni
Summary:            Kubernetes cni plugin
Group:              Applications/System

%description k8s-cni
Contrail kubernetes cni plugin package
This package contains the kubernetes cni plugin modules.

%files k8s-cni
%{_bindir}/contrail-k8s-cni


%if 0%{?_manifestFile:1}

%package manifest
BuildArch:          noarch
Summary:            Android repo manifest.xml

Group:              Applications/System

%description manifest
Manifest.xml
Used for Android repo code checkout of OpenContrail

%files manifest
/opt/contrail/manifest.xml

%endif

%endif

%package -n python3-contrail
Summary:            Contrail Python3 Lib

Group:             Applications/System
Obsoletes:         contrail-api-lib <= 0.0.1

Requires:          libev
Requires:          libev-devel

%description -n python3-contrail
Contrail common python package

The package python3-contrail provides vncAPI client library
and common api server libraries.

%files -n python3-contrail
# packaging only api client library, other python packages
# should be packaged as needed.
%{python3_sitelib}/cfgm_common*
%{python3_sitelib}/contrail_config_common*
%{python3_sitelib}/libpartition*
%{python3_sitelib}/pysandesh*
%{python3_sitelib}/sandesh-0.1*dev*
%{python3_sitelib}/sandesh_common*
%{python3_sitelib}/vnc_api*
%{python3_sitelib}/contrail_api_client*
%config(noreplace) %{_contrailetc}/vnc_api_lib.ini
/opt/opensdn/pip*

%post -n python3-contrail
set -ex

%{__python3} -m pip -v install --no-compile \
 -r /opt/opensdn/pip/api-lib/requirements.txt \
 -r /opt/opensdn/pip/libpartition/requirements.txt \
 -r /opt/opensdn/pip/sandesh-library/requirements.txt \
 -r /opt/opensdn/pip/cfgm_common/requirements.txt  |& tee /tmp/pip-common.log
