#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import datetime
from collections import namedtuple
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory import Inventory
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.utils.display import Display
from ansible.vars import VariableManager
import yaml

###############################################################################
# Se debe modificar lo siguiente                                              #
## Usuario con el que hacer ssh                                               #
USER = ''                                                                     #
## Region de aws en la que se trabajara                                       #
REGION = ''                                                                   #
## Zona en la que se trabajara                                                #
ZONE = ''                                                                     #
## Grupo de seguridad con la que se lanzara la instancia                      #
SECURITY_GROUP = ''                                                           #
## Subnet del VPC                                                             #
VPC_SUBNET = ''                                                               #
## Clave ssh remota con la que se lanzara la instancia                        #
KEYPAIR = ''                                                                  #
## Clave ssh local con la que se hara ssh                                     #
KEYFILE = ''                                                                  #
## Tipo de la instancia que se sacará. Se puede quedar el valor por defecto   #
INSTANCE_TYPE = {'paravirtual': 't1.micro', 'hvm': 't2.nano'}                 #
## Contraseña de sudo, de haberla                                             #
SUDO_PASS = None                                                              #
## Contraseña con la que hacer ssh, de haberla                                #
SSH_PASS = None                                                               #
## Pues eso                                                                   #
VERBOSITY = 0                                                                 #
###############################################################################

###############################################################################
# Consideraciones                                                             #
# extra_vars _debe_ estar en formato json                                     #
###############################################################################

# Creación e instanciación del objeto options
# Es el equivalente a pasarle opciones como parametros tipo: ansible --become
Options = namedtuple('Options', ['connection', 'module_path', 'forks',
                                 'become', 'become_method', 'become_user',
                                 'check', 'remote_user',
                                 'ansible_ssh_pass', 'private_key_file'])


# Se usa para pasar parametros. Se podria escribir en json directamente, pero
# como no nos gusta sufrir, mejor no hacerlo
def yaml2json(stream):
    """Receive yaml and convert it into json."""

    json_data = yaml.safe_load(stream)

    return json_data

# Clase principal. Se puede extender, vease el articulo de Servers For Hackers.
# Se ha mantenido al mínimo para que sea mas facil de entender.
class MakeItEasy:
    """Class to make easier to execute playbooks."""
    def __init__(self, options, playbook, extra_vars=None, loader=DataLoader(),
                 password=None, variable_manager=VariableManager(),
                 verbosity=1, host_list=None):

        # Verbosity
        display = Display()
        display.verbosity = verbosity

        # El equivalente de -e en la terminal
        self.extra_vars = extra_vars
        # Ni idea, pero es necesario
        self.loader = loader
        # Contraseña del vault, de haber
        self.passwords = password
        # Añade automaticamente las variables
        self.variable_manager = variable_manager
        # Crea un falso inventario dinámico y se lo pasa al gestor de variables
        self.inventory = Inventory(loader=loader,
                                   variable_manager=variable_manager,
                                   host_list=host_list)
        # Añade el inventario
        self.variable_manager.set_inventory(self.inventory)
        # Añade variables a mano
        if extra_vars is not None:
            self.variable_manager.extra_vars = extra_vars
        # Definir playbook
        self.playbook = playbook
        # Define opciones
        self.options = options
        # Define la lista de hosts
        self.host_list = host_list

    def run(self):
        # Instancia el objeto del playbook
        play = Play().load(self.playbook,
                           variable_manager=self.variable_manager,
                           loader=self.loader)
        # Añade el playbook a la cola
        tqm = TaskQueueManager(inventory=self.inventory,
                               variable_manager=self.variable_manager,
                               loader=self.loader,
                               options=self.options,
                               passwords=self.passwords,
                               stdout_callback=None
                              )
        # Ejecuta el playbook
        tqm.run(play)
        # Guarda los resultados de un modo mas accesible. Probablemente
        # mala practica, dado que accede a un metodo protegido.
        tqm = tqm._variable_manager._nonpersistent_fact_cache.items()

        return tqm

if __name__ == "__main__":
    # Busca amis a actualizar
    ## Variables extra en formato yaml
    extra_vars = """
base_ami:
  region : {0}
  tags:
    Upgrade: 'YES'""".format(REGION)

    ## Se pueden escribir en json directamente, como demuestra esta funcio
    extra_vars = yaml2json(extra_vars)

    ## Instancia las opciones
    options = Options(connection='local', module_path=None, forks=100,
                      become=None, become_method=None, become_user=None,
                      check=True, remote_user=None, ansible_ssh_pass=SSH_PASS,
                      private_key_file=None)

    ## El playbook en si
    playbook = dict(
        name="Find AMIs",
        hosts='localhost',
        connection='local',
        gather_facts='no',

        roles=['./roles/find-ami/']
    )

    ## Se pasa las variables a la clase gestora de playbooks...
    playbook_makeiteasy = MakeItEasy(extra_vars=extra_vars, options=options,
                                     playbook=playbook, verbosity=VERBOSITY)
    ## ... y se ejecuta
    playbook_makeiteasy = playbook_makeiteasy.run()

    ## Se hardcodea en la posicion 0 y 1 por que corresponde al host 'localhost'
    ## En AWS es siempre asi. Se hardcodea 'ami_id' por que es el nombre que
    ## registra el playbook

    results = playbook_makeiteasy[0][1]['ami_id']['results']

    # Crea instancias
    ## Inicia un par de variables
    ip = []

    ## Ejecuta un bucle con el resultado de la busqueda
    for result in results:
        ## Crea el playbook para crear instancias...
        playbook = dict(
            name="Create instance",
            hosts='localhost',
            connection='local',
            gather_facts='no',

            roles=['./roles/create-instance/'])
        virt_type = INSTANCE_TYPE[result['virtualization_type']]

        ## ... le pasa variables ...
        extra_vars = """
instance:
  name: {0}
  base_ami_id: {1}
  user: {2}
  region: {3}
  zone: {4}
  keypair: {5}
  security_groups: {6}
  type: {7}
  vpc_subnet_id: {8}
  tags:
    Name: {9}
  State: upgrading
  assign_public_ip: yes
  wait: yes
  volumes:
    device_name: /dev/sda1
    volume_size: 20,
    delete_on_termination: true""".format(result['name'], result['ami_id'],
                                              USER, REGION, ZONE, KEYPAIR,
                                              SECURITY_GROUP, virt_type,
                                              VPC_SUBNET, result['name'])

        options = Options(connection='local', module_path=None, forks=100,
                          become=None, become_method=None, become_user=None,
                          check=False, remote_user=None,
                          ansible_ssh_pass=SSH_PASS, private_key_file=None)

        extra_vars = yaml2json(extra_vars)

        ## ... y ejecuta el playbook
        playbook_makeiteasy = MakeItEasy(extra_vars=extra_vars, options=options,
                                         playbook=playbook, verbosity=VERBOSITY)

        playbook_results = playbook_makeiteasy.run()

        ins_ip = [playbook_results[-1][1]['ec2']['instances'][0]['public_ip']]
        ins_id = playbook_results[-1][1]['ec2']['instances'][0]['id']

        ## Se crean las opciones extra ...
        options = Options(connection='ssh', module_path=None, forks=100,
                          become=True, become_method='sudo', become_user='root',
                          check=False, remote_user=USER,
                          ansible_ssh_pass=SSH_PASS, private_key_file=KEYFILE)

        ## ... el playbook ...
        playbook = dict(
            name="Upgrade requests",
            gather_facts='yes',
            hosts=ins_ip,

            tasks=[
                dict(
                    action=dict(
                        module='pip',
                        args=dict(name='requests', state='latest')),
                    register='piped')
            ])



        ## ... y se ejecuta.
        playbook_makeiteasy = MakeItEasy(options=options, playbook=playbook,
                                         verbosity=VERBOSITY, host_list=ip)
        playbook_makeiteasy = playbook_makeiteasy.run()


        # Actualiza las maquinas virtuales
        ## Se concretan las opciones...
        options = Options(connection='ssh', module_path=None, forks=100,
                          become=True, become_method='sudo', become_user='root',
                          check=False, remote_user=USER,
                          ansible_ssh_pass=SSH_PASS, private_key_file=KEYFILE)

        ## ... el playbook ...
        playbook = dict(
            name="Upgrade machines",
            gather_facts='yes',
            hosts=ins_ip,

            roles=['./roles/upgrade-all/']
        )

        ## (Si se quisiese usar contraseña de sudo, se podria hacer asi)
        ## extra_vars = "ansible_become_pass: " + SUDO_PASS
        ## extra_vars = yaml2json(extra_vars)

        ## ... y se ejecuta el playbook
        playbook_makeiteasy = MakeItEasy(options=options, playbook=playbook,
                                         verbosity=VERBOSITY, host_list=ip)
        playbook_makeiteasy = playbook_makeiteasy.run()

        # Se crean las amis
        ## Se ejecuta un bucle en el diccionario de las instancias
        ## Se presupone el formato: <ENVIROMENT>-<LOGIC_COMPONENT>-<RESOURCE_TYPE>
        ##-<COMPONENT>-<LOGIC_COMPONENT_VERSION>-<DATE>
        ## para los nombres de las AMIs
        # TODO: hacer que solo se guarde la ami si habian actualizaciones

        ami_name = result['name'][:result['name'].rfind('-') + 1] + \
                   datetime.datetime.now().strftime("%Y%m%dT%H%M%S")

        ## Se crean las opciones extra ...
        extra_vars = """
ami:
  name: {0}
  region: {1}
ec2_id: {2}""".format(ami_name, REGION, ins_id)

        extra_vars = yaml2json(extra_vars)

        options = Options(connection='local', module_path=None, forks=100,
                              become=None, become_method=None, become_user=None,
                              check=False, remote_user=None,
                              ansible_ssh_pass=SSH_PASS, private_key_file=None)

        ## ... el playbook ...
        playbook = dict(
                name="Create AMI",
                hosts='localhost',
                connection='local',
                gather_facts='no',

                roles=['./roles/create-ami/'])

        ## ... y se ejecuta.
        playbook_makeiteasy = MakeItEasy(extra_vars=extra_vars,
                                             options=options,playbook=playbook,
                                             verbosity=VERBOSITY,
                                             host_list=['localhost'])
        playbook_makeiteasy = playbook_makeiteasy.run()

        ## Se coge el id de las amis nuevas de una forma muy fea
        for val in playbook_makeiteasy:
            try:
                new_ami_id = val[1]['new_ami_id']
            except:
                pass

        # Mata instancias
        ## Se concretan las opciones extra ...
        extra_vars = """
instance:
  region: {0}
  ec2_id: {1}""".format(REGION, ins_id)

        extra_vars = yaml2json(extra_vars)
        options = Options(connection='local', module_path=None, forks=100,
                              become=None, become_method=None, become_user=None,
                              check=False, remote_user=None,
                              ansible_ssh_pass=SSH_PASS, private_key_file=None)

        ## ... el playbook ...
        playbook = dict(
                name="Kill instances",
                hosts='localhost',
                connection='local',
                gather_facts='no',

                roles=['./roles/terminate-ec2/'])

        ## ... y se ejecuta
        playbook_makeiteasy = MakeItEasy(extra_vars=extra_vars,
                                             options=options, playbook=playbook,
                                             verbosity=VERBOSITY,
                                             host_list=['localhost'])
        playbook_makeiteasy = playbook_makeiteasy.run()

        if 'INT' in result['name']:
            component = 'INT'
        elif 'PORTAL' in result['name']:
            component = 'PORTAL'
        else:
            component = None

        if 'PRE' in result['name']:
            environment = 'PRE'
        elif 'PRO' in result['name']:
            environment = 'PRO'
        else:
            environment = None

        # Asignar tag a las nuevas AMIs
        ## Se concretan las opciones extra ...
        extra_vars = """
resource:
  region: {0}
  id: {1}
  tags:
    Upgrade: 'YES'
    Component: {2}
    Environment: {3}
  state: present""".format(REGION, new_ami_id, component, environment)

        extra_vars = yaml2json(extra_vars)

        options = Options(connection='local', module_path=None, forks=100,
                              become=None, become_method=None, become_user=None,
                              check=False, remote_user=None,
                              ansible_ssh_pass=SSH_PASS, private_key_file=None)

        ## ... el playbook ....
        playbook = dict(
                name="Create tags",
                hosts='localhost',
                connection='local',
                gather_facts='no',

                roles=['./roles/create-tag/'])

        ## ... y se ejecuta.
        playbook_makeiteasy = MakeItEasy(extra_vars=extra_vars,
                                             options=options, playbook=playbook,
                                             verbosity=VERBOSITY,
                                             host_list=['localhost'])
        playbook_makeiteasy = playbook_makeiteasy.run()

        # Quita los tags de las AMIs viejas
        ## Se concretan las opciones extra ...
        extra_vars = """
resource:
  region: {0}
  id: {1}
  tags:
    Upgrade: 'NO'
  state: present""".format(REGION, result['ami_id'])

        extra_vars = yaml2json(extra_vars)

        options = Options(connection='local', module_path=None, forks=100,
                          become=None, become_method=None, become_user=None,
                          check=False, remote_user=None,
                          ansible_ssh_pass=SSH_PASS, private_key_file=None)

        ## ... el playbook ...
        playbook = dict(
            name="Delete tag",
            hosts='localhost',
            connection='local',
            gather_facts='no',

            roles=['./roles/create-tag/'])

        ## ... y se ejecuta.
        playbook_makeiteasy = MakeItEasy(extra_vars=extra_vars, options=options,
                                         playbook=playbook, verbosity=VERBOSITY,
                                         host_list=['localhost'])
        playbook_makeiteasy = playbook_makeiteasy.run()
