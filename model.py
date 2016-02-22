#! /usr/bin/env python3

import json
import os
import sys
import shutil


class uml_model:

    def __init__(self, model, filename):

        self.uml = open(filename, "w")
        self.uml.write("@startuml\n")

        self._build_node(model)

        self.uml.write("@enduml\n")
        self.uml.close()


    def _build_node(self, node, level=0):

        name = node['objectInfo']['key']
        if name == "": name = "sysbus"

        path = node['objectInfo']['keyPath'] + "." + name
        if path[0] == ".": path = path[1:]

        self.uml.write('class "%s" as %s {\n' % (name, path))

        # analyse les paramètres du noeud
        if 'parameters' in node:
            for i in node['parameters']:

                access = ""
                if 'attributes' in i:
                    for j in i['attributes']:
                        if i['attributes'] == False: continue
                        if j == "read_only": access = "#"
                        elif j == "persistent": pass
                        elif j == "volatile": pass
                        else:
                            print("attribut inconnu:", j, i)
                            sys.exit(2)

                self.uml.write('  %s%s %s\n' % (access, i['type'], i['name']))

        # analyse les fonctions du noeud
        if 'functions' in node:
            for i in node['functions']:

                access = ""
                if 'attributes' in i:
                    for j in i['attributes']:
                        if i['attributes'] == False: continue
                        if j == "message": access = "~"
                        elif j == "variadic": pass
                        else:
                            print("attribut inconnu:", j, i)
                            sys.exit(2)

                arguments = []
                if 'arguments' in i:
                    for j in i['arguments']:
                        name = j['name']
                        if 'attributes' in j:
                            mandatory = False
                            out = False
                            for k, v in j['attributes'].items():
                                if k == 'out': out = v
                                elif k == 'mandatory': mandatory = v
                                elif k == 'in': pass
                                else:
                                    print("attribut inconnu:", k, j)
                                    sys.exit(2)
                            if not mandatory and not out: name = "opt " + name
                            if out: name = "out " + name
                        arguments.append(name)

                self.uml.write('  %s%s %s(%s)\n' % (access, i['type'], i['name'], ','.join(arguments)))

        self.uml.write('}\n')

        #print("%s%s" % ("    " * level, name))

        parent_path = path
        parent_name = name

        # analyse les children du noeud courant
        for child in node['children']:
            o = child['objectInfo']
            #assert(o['indexPath'] == o['keyPath'])
            assert(o['state'] == "ready")
           
            name = o['key']
            path = o['keyPath'] + "." + name

            # crée le noeud child
            self._build_node(child, level + 1)

            # lie le child au noeud courant
            self.uml.write('"%s" <-- "%s"\n' % (parent_path, path))

        # cas particulier des children non autorisés
        if 'errors' in node:
            for error in node['errors']:
                if error['error'] == 13:
                    name = error['info']
                    if name == "": name = "EMPTY"
                    path = node['objectInfo']['keyPath'] + "." + name

                    #print("%s%s *" % ("    " * (level + 1), name))

                    self.uml.write('class "%s" as %s {\n' % (name, path))
                    self.uml.write('}\n')
                    self.uml.write('"%s" <-- "%s"\n' % (parent_path, path))


def main():
    plants = []

    if not os.path.exists("model.json"):
        print("Un fichier model.json est requis.")
        print("Utiliser sysbus.py -model raw [chemin [profondeur]] pour en générer un.")
        return

    if not os.path.isdir("models"):
        os.makedirs("models")

    model = json.load(open("model.json"))

    # est-on à la racine du modèle ?
    if model['objectInfo']['keyPath'] == "" and model['objectInfo']['key'] == "":

        # on crée des diagrammes par top-level objects, sinon c'est trop gros
        for node in model['children']:
            name = node['objectInfo']['key']
            plant = "models/%s.plantuml" % name

            print("génération diagramme %s" % name)
            uml_model(node, plant)
            plants.append(plant)

        for error in model['errors']:
            if error['error'] == 13:
                name = error['info']
                print("accès interdit: %s" % name)

    else:
        print("génération diagramme")
        uml_model(model, "model.plantuml")
        plants.append('model.plantuml')

    if shutil.which("plantuml"):
        print("lancement plantuml")
        os.system("plantuml -tsvg " + ' '.join(plants))
    else:
        print("plantuml est nécessaire, vous pouvez le télécharger ici:")
        print("  OSX: brew install plantuml")
        print("  http://sourceforge.net/projects/plantuml/files/plantuml.jar/download")
        return


if __name__ == '__main__':
    main()
