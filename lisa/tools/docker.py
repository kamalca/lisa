# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from lisa.executable import Tool
from lisa.operating_system import CentOs,Debian, Redhat, Ubuntu

class Docker(Tool):

    def _install_docker_engine(self):
        self._log.debug("Installing Docker Engine on {self._node.os}}")
        
        ### UPDATE UTILS NOT NEEDED
        
        ### SWITCH CASE
        # Couldnt find Mariner, almalinux, or rockylinux in operating_system.py
        if isinstance(self._node.os, Debian) or isinstance(self._node.os, Ubuntu):
            self._log.debug("Install packages apt-transport-https ca-certificates curl gnupg-agent software-properties-common.")
            package_name = "apt-transport-https ca-certificates curl gnupg-agent software-properties-common"
            self._node.os.install_packages(package_name)
            self._log.debug("Add Docker's official GPG key.")
            #curl -fsSL https://download.docker.com/linux/$DISTRO_NAME/gpg | sudo apt-key add -
            self._log.debug("Set up the stable repository.")
            #release=$(lsb_release -cs)
            
        elif isinstance(self._node.os, Redhat) or isinstance(self._node.os, CentOs):
            pass

    """
    function InstallDockerEngine() {
        local ret=2

        LogMsg "InstallDockerEngine on $DISTRO" ###
        update_repos 
        GetOSVersion
        pack_list=(docker-ce-cli containerd.io docker-ce)
        case $DISTRO in
            ubuntu*|debian*)
                LogMsg "Uninstall old versions of Docker."
                apt-get remove -y docker docker-engine docker.io containerd runc
                LogMsg "Install packages apt-transport-https ca-certificates curl gnupg-agent software-properties-common."
                apt-get update
                install_package "apt-transport-https ca-certificates curl gnupg-agent software-properties-common"
                LogMsg "Add Docker's official GPG key."
                curl -fsSL https://download.docker.com/linux/$DISTRO_NAME/gpg | sudo apt-key add -
                LogMsg "Set up the stable repository."
                release=$(lsb_release -cs)
                add-apt-repository -y "deb https://download.docker.com/linux/$DISTRO_NAME ${release} stable"
                if [[ $os_RELEASE = '14.04' ]]; then
                    pack_list=(docker-ce)
                fi
                apt-get update
                for package in "${pack_list[@]}"; do
                    check_package "$package"
                    if [ $? -eq 0 ]; then
                        install_package "$package"
                    fi
                done
                ret=$?
            ;;

    ###################################################################################################################################

            centos*|redhat*|almalinux*|rockylinux*)
                LogMsg "Uninstall old versions of Docker."
                yum remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine
                LogMsg "Install package yum-utils."
                install_package "yum-utils"
                LogMsg "Add repo https://download.docker.com/linux/centos/docker-ce.repo."
                yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
                if [[ $DISTRO_VERSION == 8* ]];then
                    sed -i -e 's/$releasever/8/g' /etc/yum.repos.d/docker-ce.repo
                    yum install --nogpgcheck -y docker-ce docker-ce-cli containerd.io --nobest --allowerasing
                elif [[ $DISTRO_VERSION == 7* ]];then
                    yum install -y http://mirror.centos.org/centos/7/extras/x86_64/Packages/container-selinux-2.107-1.el7_6.noarch.rpm
                    for package in "${pack_list[@]}"; do
                        check_package "$package"
                        if [ $? -eq 0 ]; then
                            install_package "$package"
                        fi
                    done
                else
                    HandleSkip "Test not supported for RH/CentOS $DISTRO_VERSION" $ret
                fi
                ret=$?
            ;;

            mariner*)
                LogMsg "Docker is installed by default in $DISTRO"
                ret=0
            ;;
        *)
            HandleSkip "$DISTRO not supported" $ret
        esac
    ##########################################################################

        [[ $ret -ne 0 ]] && return $ret

        StartDockerEngine; ret=$?
        [[ $ret -ne 0 ]] && return $ret

        VerifyDockerEngine; ret=$?
        [[ $ret -ne 0 ]] && return $ret

        return $ret
    }
    """

    def _build_docker_image():
        pass

    def _run_docker_container():
        pass