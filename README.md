Tema 1 RL - Switch Implementation - Solved Tasks: 1, 2, 3

This homework covers th functionalitites of a real-life switch. All its functionalitites will be descbribed bellow

### Task1 - Forwarding
    The first task was to cover the forwardin process. The way the packets were  receoved was already covered.The way we forward
the packets is as following: We receive some packet from one of the ports. The frame has a destination MAC address. If we know that frame's. Becasue we do not know if we can reach that destiation, unless it is one of our access ports, we will store our sources MAc adressess in a MAC address table(we can reach them since we have been reached by them). Than, to actually forward the frame, we'll look through our mac table and if we find the address we are searching for , we'll send it directly (it should be one of the access ports since we could go straight to that adress). If we do not find it in our mac table, than it must be an access port for another switch, so we broadcast it to all our ports.

## Task2 - VLAN

    The VLAN is  a virtual local area network. Since we are working on a network we also have some vlans here(2 to be more
precise). Each of the access ports is in one of these vlans. If two access ports are found to have the same vlan, then they can communicate one to each other. We also have some trunk ports, in between the switches. A trunk is an area were every every frame, no mater its vlan, can go through. So, my implemetation goes over the basic forwarding, but first, for each switch, we need to read its configurations. Function 'read_configs' does exactly that reading all of the switch's configurations(all its ports, and the type of connection: trunk or basic vlan). We store all our configurations in a map, for each switch. We also are able to note from what vlan the frame came from (made from how we receive the frame). If the vlan is not marked, we do by looking in th configs table. Than we have two cases, that eventually become four. If a frame is sent to a trunk port, it needs to contain an 802.1Q header. So on the cases when the frame goes from access port to access port and from trunk port to trunk port, we do not have to do anything. In the case we are sending it from an acces port to a trunk port we need to add that header after the source mac field, and also we need to remove that header if the frame goes from an trunk port to an access port. 

## Task 3 - Spanning Tree Protocol
    This portocol is used to block any ports that colud potentilly make a loop, and forward the frame forever. What we'll do is
implement a simpler stp like protocol. First, what we need to do is to initialize state for each port. Initially we will consider all the access ports to be designated(or listening), and all our thrunk ports to blocking(there is no way we can have loops on a access port). Than, we send a bdpu package every second to all the other switches. This is done only from the root bridge, but for starters all th swihces start as the root so they all send bdpu packages to each other. We update all our fields, so we'll know we are the route (Fields is_root, root_port, my_bridge_id, root_bridge_id, root_path_cost are all stored globally beacause w need to constatlly update them, and the changes need to be made on the spot, as well as the all our tables of states, mac addresses and of the types of the ports). At the other end, when we receive a bdpu frame we will handle its content. First, if its root_brige_ID is lower than our own ID we know that we can no longer be root, and that specific switch is our root. We increase out root_path_cost with ten, and we also make all our trunk ports except the one communicating with the root to blocking. We are no longer the root. If the port was blocking, we switch it to listening, and at the end we update all our trunk neighbours of the changes made. If we already know that we are not the root and receive a frame from the route, we check if it was received directly from the route, and if so we update its cost if needed. If we do not receive it directly from the root, we check if we do not have a less expensive port already. If we do not we'll make it to listening. If we receive that frame from out own bridge id, it means there is a loop, so we set the state to blocking .If our own bridge ID is the root bridge ID we'll set all our ports to listning state. Something that should also be said is that we do not use the propper bdpu, we have a bdpu like protocol, the differences being that not all of the bdpu's fields are importnat to us, so we use just some relevant ones

